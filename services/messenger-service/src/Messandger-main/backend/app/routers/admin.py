from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User, AccessRequest, Department, Division, ProfileChangeRequest
from app.models.chat import Chat, ChatMember
from app.services.auth import get_current_user

router = APIRouter(prefix="/api/admin", tags=["admin"])


def require_admin(current_user: User = Depends(get_current_user)):
    if current_user.role not in ('super_admin', 'admin'):
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    return current_user


# ===========================================================================
# УПРАВЛЕНИЕ ЗАПРОСАМИ НА ДОСТУП
# ===========================================================================

@router.get("/access-requests")
async def list_access_requests(
    status: str = "pending",
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    query = select(AccessRequest)
    if status:
        query = query.where(AccessRequest.status == status)
    query = query.order_by(AccessRequest.created_at.desc())
    result = await db.execute(query)
    requests = result.scalars().all()
    return [{
        "id": str(r.id),
        "first_name": r.first_name,
        "last_name": r.last_name,
        "patronymic": r.patronymic,
        "email": r.email,
        "phone": r.phone,
        "department_id": str(r.department_id) if r.department_id else None,
        "division_id": str(r.division_id) if r.division_id else None,
        "position": r.position,
        "reason": r.reason,
        "status": r.status,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    } for r in requests]


@router.post("/access-requests/{request_id}/approve")
async def approve_access_request(
    request_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    import uuid as uuid_mod
    result = await db.execute(select(AccessRequest).where(AccessRequest.id == uuid_mod.UUID(request_id)))
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Запрос не найден")
    if req.status != "pending":
        raise HTTPException(status_code=400, detail="Запрос уже обработан")

    auth_user_id = data.get("auth_user_id")
    if not auth_user_id:
        raise HTTPException(
            status_code=400,
            detail="Укажите auth_user_id — UUID пользователя из auth-service",
        )

    user = User(
        id=uuid_mod.UUID(auth_user_id),
        email=req.email,
        first_name=req.first_name,
        last_name=req.last_name,
        patronymic=req.patronymic,
        phone=req.phone,
        department_id=req.department_id,
        division_id=req.division_id,
        position=req.position,
        role=data.get("role", "user"),
    )
    db.add(user)
    await db.flush()

    # Подписать на новостной канал
    news_result = await db.execute(select(Chat).where(Chat.is_news_channel == True))
    news_channel = news_result.scalar_one_or_none()
    if news_channel:
        member = ChatMember(chat_id=news_channel.id, user_id=user.id, role="readonly")
        db.add(member)

    # Создать "Избранное"
    saved_chat = Chat(chat_type="saved", name="Избранное", owner_id=user.id)
    db.add(saved_chat)
    await db.flush()
    saved_member = ChatMember(chat_id=saved_chat.id, user_id=user.id, role="owner")
    db.add(saved_member)

    # Обновить запрос
    req.status = "approved"
    req.reviewed_by = admin.id
    req.reviewed_at = datetime.utcnow()

    return {"message": f"Профиль мессенджера для {req.email} создан", "user_id": str(user.id)}


@router.post("/access-requests/{request_id}/reject")
async def reject_access_request(
    request_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    import uuid as uuid_mod
    result = await db.execute(select(AccessRequest).where(AccessRequest.id == uuid_mod.UUID(request_id)))
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Запрос не найден")

    req.status = "rejected"
    req.reviewed_by = admin.id
    req.review_comment = data.get("comment", "")
    req.reviewed_at = datetime.utcnow()
    return {"message": "Запрос отклонён"}


# ===========================================================================
# УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ
# ===========================================================================

@router.get("/users")
async def list_users(
    q: str = "",
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    query = select(User)
    if q:
        query = query.where(
            (User.first_name.ilike(f"%{q}%")) |
            (User.last_name.ilike(f"%{q}%")) |
            (User.email.ilike(f"%{q}%"))
        )
    query = query.order_by(User.last_name, User.first_name).limit(100)
    result = await db.execute(query)
    users = result.scalars().all()
    return [{
        "id": str(u.id),
        "email": u.email,
        "first_name": u.first_name,
        "last_name": u.last_name,
        "patronymic": u.patronymic,
        "position": u.position,
        "role": u.role,
        "is_active": u.is_active,
        "is_blocked": u.is_blocked,
        "is_frozen": u.is_frozen,
        "department_id": str(u.department_id) if u.department_id else None,
        "created_at": u.created_at.isoformat() if u.created_at else None,
    } for u in users]


@router.post("/users/create")
async def create_user(data: dict, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    existing = await db.execute(select(User).where(User.email == data.get("email")))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email уже используется")

    auth_user_id = data.get("id") or data.get("auth_user_id")
    if not auth_user_id:
        raise HTTPException(status_code=400, detail="Укажите id (UUID из auth-service)")

    import uuid as uuid_mod
    user = User(
        id=uuid_mod.UUID(auth_user_id),
        email=data["email"],
        first_name=data["first_name"],
        last_name=data["last_name"],
        patronymic=data.get("patronymic"),
        phone=data.get("phone"),
        department_id=data.get("department_id"),
        division_id=data.get("division_id"),
        position=data.get("position"),
        role=data.get("role", "user"),
    )
    db.add(user)
    await db.flush()

    # Подписать на новостной канал
    news_result = await db.execute(select(Chat).where(Chat.is_news_channel == True))
    news_channel = news_result.scalar_one_or_none()
    if news_channel:
        db.add(ChatMember(chat_id=news_channel.id, user_id=user.id, role="readonly"))

    # Создать "Избранное"
    saved_chat = Chat(chat_type="saved", name="Избранное", owner_id=user.id)
    db.add(saved_chat)
    await db.flush()
    db.add(ChatMember(chat_id=saved_chat.id, user_id=user.id, role="owner"))

    return {"message": "Профиль мессенджера создан", "user_id": str(user.id)}


@router.put("/users/{user_id}")
async def update_user(user_id: str, data: dict, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    import uuid as uuid_mod
    result = await db.execute(select(User).where(User.id == uuid_mod.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    allowed_fields = ["first_name", "last_name", "patronymic", "position", "role", "department_id", "division_id", "phone"]
    for field in allowed_fields:
        if field in data:
            setattr(user, field, data[field])
    db.add(user)
    return {"message": "Пользователь обновлён"}


@router.post("/users/{user_id}/block")
async def block_user(user_id: str, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    import uuid as uuid_mod
    result = await db.execute(select(User).where(User.id == uuid_mod.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    user.is_blocked = True
    return {"message": "Пользователь заблокирован"}


@router.post("/users/{user_id}/unblock")
async def unblock_user(user_id: str, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    import uuid as uuid_mod
    result = await db.execute(select(User).where(User.id == uuid_mod.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    user.is_blocked = False
    return {"message": "Пользователь разблокирован"}


@router.post("/users/{user_id}/freeze")
async def freeze_user(user_id: str, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    import uuid as uuid_mod
    result = await db.execute(select(User).where(User.id == uuid_mod.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    user.is_frozen = True
    return {"message": "Аккаунт заморожен"}


@router.post("/users/{user_id}/unfreeze")
async def unfreeze_user(user_id: str, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    import uuid as uuid_mod
    result = await db.execute(select(User).where(User.id == uuid_mod.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    user.is_frozen = False
    return {"message": "Аккаунт разморожен"}


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    import uuid as uuid_mod
    result = await db.execute(select(User).where(User.id == uuid_mod.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    user.is_active = False
    return {"message": "Пользователь удалён"}


@router.post("/users/{user_id}/reset-password")
async def reset_password(user_id: str, data: dict, admin: User = Depends(require_admin)):
    raise HTTPException(
        status_code=410,
        detail="Сброс пароля выполняется в auth-service / портале, не в мессенджере.",
    )


# ===========================================================================
# ЗАПРОСЫ НА ИЗМЕНЕНИЕ ПРОФИЛЯ
# ===========================================================================

@router.get("/profile-requests")
async def list_profile_requests(db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    result = await db.execute(
        select(ProfileChangeRequest).where(ProfileChangeRequest.status == "pending").order_by(ProfileChangeRequest.created_at.desc())
    )
    requests = result.scalars().all()
    return [{
        "id": str(r.id),
        "user_id": str(r.user_id),
        "field_name": r.field_name,
        "old_value": r.old_value,
        "new_value": r.new_value,
        "status": r.status,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    } for r in requests]


@router.post("/profile-requests/{request_id}/approve")
async def approve_profile_request(request_id: str, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    import uuid as uuid_mod
    from app.auth_client import auth_client

    result = await db.execute(select(ProfileChangeRequest).where(ProfileChangeRequest.id == uuid_mod.UUID(request_id)))
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Запрос не найден")

    # Применить изменение
    user_result = await db.execute(select(User).where(User.id == req.user_id))
    user = user_result.scalar_one_or_none()
    if user:
        setattr(user, req.field_name, req.new_value)
        db.add(user)

        # Если изменились ФИО — синхронизировать с auth-service
        if req.field_name in ("first_name", "last_name", "patronymic"):
            # Собрать full_name из текущих значений (с учётом изменения)
            first = user.first_name if req.field_name != "first_name" else req.new_value
            last = user.last_name if req.field_name != "last_name" else req.new_value
            patronymic = user.patronymic if req.field_name != "patronymic" else req.new_value
            parts = [p for p in (first, last, patronymic) if p]
            full_name = " ".join(parts) if parts else None
            if full_name:
                await auth_client.update_user(str(user.id), full_name=full_name)

    req.status = "approved"
    req.reviewed_by = admin.id
    req.reviewed_at = datetime.utcnow()
    db.add(req)

    await db.commit()
    return {"message": "Изменение применено"}


@router.post("/profile-requests/{request_id}/reject")
async def reject_profile_request(request_id: str, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    import uuid as uuid_mod
    result = await db.execute(select(ProfileChangeRequest).where(ProfileChangeRequest.id == uuid_mod.UUID(request_id)))
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Запрос не найден")
    req.status = "rejected"
    req.reviewed_by = admin.id
    req.reviewed_at = datetime.utcnow()
    return {"message": "Запрос отклонён"}


# ===========================================================================
# АУДИТ / МОНИТОРИНГ / БЭКАПЫ
# ===========================================================================

from app.models.audit import AuditLog
from app.services import metrics as _metrics
from app.services import backup as _backup
from app.services.audit import audit as _audit
from app.routers.websocket import manager as _ws_manager
from fastapi.responses import FileResponse
import os as _os


@router.get("/audit-log")
async def get_audit_log(
    action: str | None = None,
    actor_id: str | None = None,
    status_filter: str | None = None,
    limit: int = 200,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Журнал аудита. Доступен только администраторам."""
    q = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(min(max(1, limit), 1000))
    if action:
        q = q.where(AuditLog.action == action)
    if status_filter:
        q = q.where(AuditLog.status == status_filter)
    if actor_id:
        import uuid as _uuid
        try:
            q = q.where(AuditLog.actor_id == _uuid.UUID(actor_id))
        except Exception:
            pass
    res = await db.execute(q)
    rows = res.scalars().all()
    return [{
        "id": str(r.id),
        "actor_id": str(r.actor_id) if r.actor_id else None,
        "actor_email": r.actor_email,
        "action": r.action,
        "object_type": r.object_type,
        "object_id": r.object_id,
        "ip_address": r.ip_address,
        "user_agent": r.user_agent,
        "status": r.status,
        "details": r.details,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    } for r in rows]


@router.get("/metrics")
async def get_metrics(admin: User = Depends(require_admin)):
    """Текущие in-memory метрики приложения + параметры окружения."""
    from app.config import settings as _settings
    snap = _metrics.snapshot()
    snap["ws_active"] = len(_ws_manager.active_connections)
    snap["env"] = _settings.ENV
    snap["db_url_kind"] = "sqlite" if "sqlite" in _settings.DATABASE_URL else "postgresql" if "postgresql" in _settings.DATABASE_URL else "other"
    snap["db_encrypted"] = bool(_settings.DB_ENCRYPTION_KEY)
    return snap


@router.get("/backups")
async def list_backups_endpoint(admin: User = Depends(require_admin)):
    return _backup.list_backups()


@router.post("/backups")
async def create_backup_endpoint(admin: User = Depends(require_admin)):
    """Создать бэкап БД немедленно."""
    import asyncio as _asyncio
    meta = await _asyncio.to_thread(_backup.create_backup_sync, "manual")
    if not meta:
        raise HTTPException(status_code=500, detail="Не удалось создать бэкап")
    await _audit("backup_create", actor_id=str(admin.id), actor_email=admin.email,
                 object_type="system", object_id=meta["file"], details=meta)
    return meta


@router.get("/backups/{filename}/download")
async def download_backup(filename: str, admin: User = Depends(require_admin)):
    # Защита от path traversal
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Недопустимое имя файла")
    from app.config import settings as _settings
    path = _os.path.join(_settings.BACKUP_DIR, filename)
    if not _os.path.exists(path):
        raise HTTPException(status_code=404, detail="Файл не найден")
    await _audit("backup_download", actor_id=str(admin.id), actor_email=admin.email,
                 object_type="system", object_id=filename)
    return FileResponse(path, media_type="application/gzip", filename=filename)


@router.get("/db-integrity")
async def db_integrity(admin: User = Depends(require_admin)):
    """Проверка целостности БД (PRAGMA integrity_check)."""
    import asyncio as _asyncio
    res = await _asyncio.to_thread(_backup.check_db_integrity_sync)
    if not res["ok"]:
        await _audit("db_integrity_fail", actor_id=str(admin.id), actor_email=admin.email,
                     status="failed", details=res)
    return res
