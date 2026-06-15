"""Глобальная обработка ошибок, безопасность и метрики."""
import logging
import time
import traceback
import uuid
from collections import defaultdict, deque
from typing import Dict, Deque

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.services import metrics
from app.services.audit import audit

logger = logging.getLogger("app")


# ---------------------------------------------------------------------------
# Простой in-memory rate limiter (sliding window) для всех неаутентифицированных
# и тяжёлых эндпоинтов. На прод желательно вынести в Redis.
# ---------------------------------------------------------------------------
_BUCKET: Dict[str, Deque[float]] = defaultdict(deque)
RATE_LIMITS = {
    # path_prefix -> (max_requests, window_seconds)
    "/api/auth/login": (10, 60),
    "/api/auth/access-request": (5, 300),
    "/api/auth/me/avatar/upload": (10, 60),
}
DEFAULT_LIMIT = (300, 60)  # глобально 300 req/min/IP


def _rate_check(ip: str, path: str) -> bool:
    """True если можно пропустить, False если превышен лимит."""
    now = time.time()
    limit, window = DEFAULT_LIMIT
    for prefix, lw in RATE_LIMITS.items():
        if path.startswith(prefix):
            limit, window = lw
            break
    key = f"{ip}|{path if path in RATE_LIMITS else '*'}"
    bucket = _BUCKET[key]
    cutoff = now - window
    while bucket and bucket[0] < cutoff:
        bucket.popleft()
    if len(bucket) >= limit:
        return False
    bucket.append(now)
    return True


def register_middleware(app: FastAPI):
    @app.middleware("http")
    async def _rate_limit_and_logging(request: Request, call_next):
        request_id = uuid.uuid4().hex[:12]
        ip = request.client.host if request.client else "unknown"

        # Rate limit
        if not _rate_check(ip, request.url.path):
            metrics.inc("rate_limited")
            await audit(
                "rate_limit_exceeded",
                ip_address=ip,
                object_type="http",
                object_id=request.url.path,
                status="warning",
            )
            return JSONResponse(
                status_code=429,
                content={"detail": "Слишком много запросов. Попробуйте позже.", "request_id": request_id},
            )

        # Лимит размера тела запроса для защиты от DoS (50 МБ; uploads допускаем больше через отдельный путь)
        cl = request.headers.get("content-length")
        max_body = 50 * 1024 * 1024
        if request.url.path.startswith("/api/chats") and "/upload" in request.url.path:
            max_body = 200 * 1024 * 1024  # 200 МБ для файлов
        try:
            if cl is not None and int(cl) > max_body:
                metrics.inc("payload_too_large")
                return JSONResponse(
                    status_code=413,
                    content={"detail": "Запрос превышает допустимый размер", "request_id": request_id},
                )
        except ValueError:
            pass

        metrics.inc("request_total")
        start = time.time()
        try:
            response = await call_next(request)
        except Exception as exc:  # noqa
            metrics.inc("http_5xx")
            logger.error(
                "[%s] unhandled %s %s ip=%s: %s\n%s",
                request_id, request.method, request.url.path, ip, exc, traceback.format_exc(),
            )
            await audit(
                "unhandled_exception",
                ip_address=ip,
                object_type="http",
                object_id=request.url.path,
                status="failed",
                details={"error": str(exc), "request_id": request_id},
            )
            return JSONResponse(
                status_code=500,
                content={
                    "detail": "Внутренняя ошибка сервера. Обратитесь в Управление информатизации.",
                    "request_id": request_id,
                },
            )

        elapsed_ms = int((time.time() - start) * 1000)
        if response.status_code >= 500:
            metrics.inc("http_5xx")
        elif response.status_code >= 400:
            metrics.inc("http_4xx")
        else:
            metrics.inc("http_2xx_3xx")

        response.headers["X-Request-Id"] = request_id
        response.headers["X-Response-Time-Ms"] = str(elapsed_ms)
        return response

    @app.middleware("http")
    async def _security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(self), camera=(self), "
            "display-capture=(self), payment=(), usb=()"
        )
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-XSS-Protection"] = "0"
        # Жёсткий CSP для API (фронт у нас отдельным сервером — не ломает SPA, т.к. там свой CSP)
        if request.url.path.startswith("/api/"):
            response.headers["Content-Security-Policy"] = (
                "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
            )
        return response


def register_exception_handlers(app: FastAPI):
    @app.exception_handler(StarletteHTTPException)
    async def _http_exc(request: Request, exc: StarletteHTTPException):
        if exc.status_code >= 500:
            metrics.inc("http_5xx")
        elif exc.status_code >= 400:
            metrics.inc("http_4xx")
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError):
        metrics.inc("http_4xx")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": "Ошибка валидации входных данных", "errors": exc.errors()},
        )

    @app.exception_handler(SQLAlchemyError)
    async def _db_error(request: Request, exc: SQLAlchemyError):
        metrics.inc("http_5xx")
        logger.error("DB error on %s: %s", request.url.path, exc)
        await audit(
            "db_error",
            ip_address=request.client.host if request.client else None,
            object_type="db",
            object_id=request.url.path,
            status="failed",
            details={"error": str(exc)[:300]},
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Ошибка базы данных. Запрос не выполнен."},
        )
