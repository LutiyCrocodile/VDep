import uuid as uuid_mod
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.user import User
from app.models.notification import Notification
from app.services.auth import get_current_user
from app.routers.websocket import manager

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


def require_admin(current_user: User = Depends(get_current_user)):
    if current_user.role not in ('super_admin', 'admin'):
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    return current_user


# ===========================================================================
# ПОЛЬЗОВАТЕЛЬСКИЕ УВЕДОМЛЕНИЯ
# ===========================================================================

@router.get("/")
async def get_notifications(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
    )
    notifications = result.scalars().all()
    return [{
        "id": str(n.id),
        "type": n.type,
        "title": n.title,
        "body": n.body,
        "data": n.data,
        "is_read": n.is_read,
        "created_at": n.created_at.isoformat() if n.created_at else None,
    } for n in notifications]


@router.get("/unread-count")
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(func.count(Notification.id))
        .where(Notification.user_id == current_user.id, Notification.is_read == False)
    )
    count = result.scalar() or 0
    return {"count": count}


@router.post("/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Notification).where(
            Notification.id == uuid_mod.UUID(notification_id),
            Notification.user_id == current_user.id
        )
    )
    n = result.scalar_one_or_none()
    if n:
        n.is_read = True
    return {"ok": True}


@router.post("/read-all")
async def mark_all_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Notification).where(
            Notification.user_id == current_user.id,
            Notification.is_read == False
        )
    )
    for n in result.scalars().all():
        n.is_read = True
    return {"ok": True}


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Notification).where(
            Notification.id == uuid_mod.UUID(notification_id),
            Notification.user_id == current_user.id
        )
    )
    n = result.scalar_one_or_none()
    if n:
        await db.delete(n)
    return {"ok": True}


# ===========================================================================
# АДМИН: ОТПРАВКА УВЕДОМЛЕНИЙ И ПРЕДУПРЕЖДЕНИЙ
# ===========================================================================

@router.post("/send")
async def send_notification(
    data: dict,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """
    Отправить уведомление.
    data:
      - type: 'announcement' | 'warning' | 'info' | 'system'
      - title: str
      - body: str
      - target: 'all' | 'department' | 'user'
      - department_id: str (if target='department')
      - user_ids: list[str] (if target='user')
    """
    notif_type = data.get("type", "announcement")
    title = data.get("title", "")
    body = data.get("body", "")
    target = data.get("target", "all")

    if not title:
        raise HTTPException(status_code=400, detail="Укажите заголовок")

    user_ids = []

    if target == "all":
        result = await db.execute(select(User).where(User.is_active == True))
        user_ids = [u.id for u in result.scalars().all()]
    elif target == "department":
        dept_id = data.get("department_id")
        if not dept_id:
            raise HTTPException(status_code=400, detail="Укажите управление")
        result = await db.execute(
            select(User).where(User.is_active == True, User.department_id == uuid_mod.UUID(dept_id))
        )
        user_ids = [u.id for u in result.scalars().all()]
    elif target == "user":
        raw_ids = data.get("user_ids", [])
        user_ids = [uuid_mod.UUID(uid) for uid in raw_ids]

    count = 0
    for uid in user_ids:
        n = Notification(
            user_id=uid,
            type=notif_type,
            title=title,
            body=body,
            data={"sender_id": str(admin.id), "sender_name": f"{admin.first_name} {admin.last_name}"},
        )
        db.add(n)
        count += 1

    await db.flush()

    # Push via WebSocket
    for uid in user_ids:
        await manager.send_to_user(str(uid), {
            "type": "notification",
            "title": title,
            "body": body,
            "notif_type": notif_type,
        })

    return {"message": f"Уведомление отправлено ({count} получателей)", "count": count}


@router.get("/sent")
async def get_sent_notifications(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Получить историю отправленных уведомлений (по отправителю)."""
    result = await db.execute(
        select(Notification)
        .where(Notification.data["sender_id"].as_string() == str(admin.id))
        .order_by(Notification.created_at.desc())
        .limit(100)
    )
    notifications = result.scalars().all()
    # Группируем по уникальным (title, body, created_at)
    seen = set()
    items = []
    for n in notifications:
        key = (n.title, n.body, n.created_at.isoformat() if n.created_at else "")
        if key not in seen:
            seen.add(key)
            items.append({
                "id": str(n.id),
                "type": n.type,
                "title": n.title,
                "body": n.body,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            })
    return items
