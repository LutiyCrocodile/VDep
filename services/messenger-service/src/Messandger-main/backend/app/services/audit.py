"""Сервис журнала аудита. Использовать `audit(...)` из любого места кода."""
import json
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Request

from app.database import async_session
from app.models.audit import AuditLog

logger = logging.getLogger("audit")


async def audit(
    action: str,
    *,
    actor_id: Optional[str] = None,
    actor_email: Optional[str] = None,
    object_type: Optional[str] = None,
    object_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    status: str = "success",
    details: Optional[dict] = None,
    request: Optional[Request] = None,
    db: Optional[AsyncSession] = None,
):
    """Записать событие в журнал аудита. Безопасна: глотает любые ошибки и пишет их в лог."""
    try:
        import uuid as _uuid
        # Достаём IP / UA из request, если переданы
        if request is not None:
            ip_address = ip_address or (request.client.host if request.client else None)
            user_agent = user_agent or request.headers.get("user-agent", "")[:300]

        actor_uuid = None
        if actor_id:
            try:
                actor_uuid = _uuid.UUID(str(actor_id))
            except Exception:
                actor_uuid = None

        entry = AuditLog(
            actor_id=actor_uuid,
            actor_email=actor_email,
            action=action,
            object_type=object_type,
            object_id=str(object_id) if object_id is not None else None,
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
            details=json.dumps(details, ensure_ascii=False, default=str) if details else None,
        )

        # Если сессия передана — используем её (часть текущей транзакции),
        # иначе открываем независимую, чтобы аудит писался даже при rollback основной операции.
        if db is not None:
            db.add(entry)
        else:
            async with async_session() as s:
                s.add(entry)
                await s.commit()

        logger.info(
            "AUDIT action=%s status=%s actor=%s obj=%s/%s ip=%s",
            action, status, actor_id, object_type, object_id, ip_address,
        )
    except Exception as e:
        logger.error("audit write failed: %s", e)
