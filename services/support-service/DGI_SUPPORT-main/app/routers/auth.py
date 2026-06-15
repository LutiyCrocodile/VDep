from __future__ import annotations

from pathlib import Path
import re
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.exceptions import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import PORTAL_URL
from app.core.templates import templates
from app.core.deps import get_current_user, get_current_user_optional
from app.db.models import User
from app.db.session import get_db

router = APIRouter()


_RE_INTERNAL_NUMBER = re.compile(r"^\d{2}-\d{3}$")
_RE_OFFICE = re.compile(r"^\d{2}\.\d{2}$")
_RE_USERNAME = re.compile(r"^[a-zA-Z0-9_]{3,30}$")


def _validate_password(password: str) -> str | None:
    """Validate password strength. Returns error message if invalid, None if valid."""
    if len(password) < 8:
        return "Пароль должен быть минимум 8 символов"
    if not re.search(r"[A-Z]", password):
        return "Пароль должен содержать хотя бы одну заглавную букву"
    if not re.search(r"[a-z]", password):
        return "Пароль должен содержать хотя бы одну строчную букву"
    if not re.search(r"\d", password):
        return "Пароль должен содержать хотя бы одну цифру"
    return None

_AVATAR_UPLOAD_DIR = Path("app") / "media" / "avatars"
_AVATAR_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    # Always redirect to portal for authentication
    # Portal will pass tokens via query params if user is logged in
    return RedirectResponse(url=f"{PORTAL_URL.rstrip('/')}/login", status_code=303)


@router.get("/profile", response_class=HTMLResponse)
async def profile_form(request: Request, user: User = Depends(get_current_user)):
    return templates.TemplateResponse(request, "profile.html", {"user": user, "error": None})


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, user: User = Depends(get_current_user)):
    return templates.TemplateResponse(request, "settings.html", {"user": user})


@router.post("/profile")
async def profile_update(
    request: Request,
    internal_number: str = Form(""),
    office: str = Form(""),
    avatar: UploadFile | None = File(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    internal_number = internal_number.strip() or None
    office = office.strip() or None

    if internal_number and not _RE_INTERNAL_NUMBER.match(internal_number):
        return templates.TemplateResponse(
            request,
            "profile.html",
            {"user": user, "error": "Внутренний номер должен быть в формате 21-666"},
            status_code=400,
        )

    if office and not _RE_OFFICE.match(office):
        return templates.TemplateResponse(
            request,
            "profile.html",
            {"user": user, "error": "Кабинет должен быть в формате 18.26"},
            status_code=400,
        )

    result = await db.execute(select(User).filter(User.id == user.id))
    u = result.scalar_one_or_none()
    if not u:
        return RedirectResponse(url=f"{PORTAL_URL.rstrip('/')}/login", status_code=303)

    u.internal_number = internal_number
    u.office = office

    if avatar is not None and avatar.filename:
        ct = (avatar.content_type or "").lower()
        if ct in ("image/jpeg", "image/png", "image/webp"):
            ext = ".jpg" if ct == "image/jpeg" else (".png" if ct == "image/png" else ".webp")
            name = f"{u.id}_{uuid4().hex}{ext}"
            dest = _AVATAR_UPLOAD_DIR / name
            dest.write_bytes(await avatar.read())
            u.avatar_path = f"/media/avatars/{name}"

    await db.commit()
    return RedirectResponse(url="/profile", status_code=303)


@router.post("/logout")
async def logout():
    resp = RedirectResponse(url=f"{PORTAL_URL.rstrip('/')}/login", status_code=303)
    resp.delete_cookie("support_access_token")
    resp.delete_cookie("support_refresh_token")
    return resp


# Disable local registration/login - use portal/auth-service instead
@router.post("/login")
async def login_disabled():
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Вход выполняется через портал ДГИ. Перейдите на портал и откройте техподдержку из списка сервисов.",
    )


@router.post("/register")
async def register_disabled():
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Регистрация выполняется через портал ДГИ. Перейдите на портал для создания учётной записи.",
    )
