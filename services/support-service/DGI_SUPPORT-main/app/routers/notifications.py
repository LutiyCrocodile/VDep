from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.templates import templates
from app.core.deps import get_current_user, require_role
from app.db.models import Broadcast, Notification, User, UserRole
from app.db.session import get_db

router = APIRouter(prefix="/notifications")


# ── API: unread count ────────────────────────────────────────────────
@router.get("/count")
async def notification_count(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Notification).filter(
            Notification.user_id == user.id,
            Notification.is_read == False,
        )
    )
    count = len(result.scalars().all())
    return {"count": count}


# ── API: mark as read ────────────────────────────────────────────────
@router.post("/{notification_id}/read")
async def mark_read(
    notification_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Notification).filter(Notification.id == notification_id))
    n = result.scalar_one_or_none()
    if n and n.user_id == user.id:
        n.is_read = True
        await db.commit()
    return {"ok": True}


# ── API: mark all as read ────────────────────────────────────────────
@router.post("/read-all")
async def mark_all_read(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Notification).filter(
            Notification.user_id == user.id,
            Notification.is_read == False,
        )
    )
    notifications = result.scalars().all()
    for n in notifications:
        n.is_read = True
    await db.commit()
    return {"ok": True}


# ── API: delete notification ─────────────────────────────────────────
@router.post("/{notification_id}/delete")
async def delete_notification(
    notification_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Notification).filter(Notification.id == notification_id))
    n = result.scalar_one_or_none()
    if n and n.user_id == user.id:
        await db.delete(n)
        await db.commit()
    return {"ok": True}


# ── API: delete all personal notifications ────────────────────────────
@router.post("/clear-all")
async def clear_all_notifications(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Notification).filter(
            Notification.user_id == user.id,
            Notification.broadcast_id == None,
        )
    )
    notifications = result.scalars().all()
    for n in notifications:
        await db.delete(n)
    await db.commit()
    return {"ok": True}


# ── Page: notification list ──────────────────────────────────────────
@router.get("", response_class=HTMLResponse)
async def notification_list(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    notif_result = await db.execute(
        select(Notification)
        .filter(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
    )
    notifications = notif_result.scalars().all()
    
    broadcast_result = await db.execute(
        select(Broadcast)
        .order_by(Broadcast.created_at.desc())
    )
    broadcasts = broadcast_result.scalars().all()
    
    return templates.TemplateResponse(
        request,
        "notifications.html",
        {
            "user": user,
            "notifications": notifications,
            "broadcasts": broadcasts,
        },
    )


# ── Admin: create broadcast ──────────────────────────────────────────
@router.post("/broadcast")
async def create_broadcast(
    title: str = Form(...),
    body: str = Form(""),
    user: User = Depends(require_role(UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    bc = Broadcast(
        author_id=user.id,
        title=title.strip(),
        body=body.strip(),
    )
    db.add(bc)
    await db.commit()
    return RedirectResponse(url="/notifications", status_code=303)


# ── Admin: delete broadcast ──────────────────────────────────────────
@router.post("/broadcast/{broadcast_id}/delete")
async def delete_broadcast(
    broadcast_id: int,
    user: User = Depends(require_role(UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Broadcast).filter(Broadcast.id == broadcast_id))
    bc = result.scalar_one_or_none()
    if bc:
        # Удалить связанные уведомления
        notif_result = await db.execute(
            select(Notification).filter(Notification.broadcast_id == broadcast_id)
        )
        notifications = notif_result.scalars().all()
        for n in notifications:
            await db.delete(n)
        await db.delete(bc)
        await db.commit()
    return RedirectResponse(url="/notifications", status_code=303)
