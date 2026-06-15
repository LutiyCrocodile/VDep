from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.deps import require_role
from app.core.templates import templates
from app.db.models import Equipment, Ticket, User, UserRole
from app.db.session import get_db

router = APIRouter(prefix="/users")


@router.get("/search")
async def user_search(
    request: Request,
    q: str = "",
    role: str = "",
    db: AsyncSession = Depends(get_db),
):
    query = select(User).filter(User.is_active == True)
    if role:
        try:
            # For engineer role, also include admins
            if role == "engineer":
                query = query.filter(User.role.in_([UserRole.engineer, UserRole.admin]))
            else:
                query = query.filter(User.role == UserRole(role))
        except Exception:
            pass
    if q:
        query = query.filter(
            or_(
                User.full_name.ilike(f"%{q}%"),
                User.username.ilike(f"%{q}%"),
            )
        )
    result = await db.execute(query.order_by(User.full_name.asc()).limit(20))
    results = result.scalars().all()
    return JSONResponse([
        {"id": str(u.id), "label": f"{u.full_name or u.username} ({u.office or '—'})"}
        for u in results
    ])


@router.get("", response_class=HTMLResponse)
async def users_list(
    request: Request,
    user: User = Depends(require_role(UserRole.engineer, UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    q = (request.query_params.get("q") or "").strip()

    query = select(User)
    if q:
        query = query.filter(
            or_(
                User.username.ilike(f"%{q}%"),
                User.full_name.ilike(f"%{q}%"),
                User.position.ilike(f"%{q}%"),
                User.office.ilike(f"%{q}%"),
                User.internal_number.ilike(f"%{q}%"),
            )
        )

    result = await db.execute(query.order_by(User.full_name.asc()))
    users = result.scalars().all()
    return templates.TemplateResponse(request, "users_list.html", {"user": user, "users": users, "q": q})


@router.get("/{user_id}", response_class=HTMLResponse)
async def user_detail(
    user_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    import uuid as uuid_mod
    try:
        user_uuid = uuid_mod.UUID(user_id)
    except ValueError:
        return RedirectResponse(url="/users", status_code=303)

    if user.role == UserRole.user and user_uuid != user.id:
        return RedirectResponse(url="/profile", status_code=303)

    result = await db.execute(select(User).filter(User.id == user_uuid))
    u = result.scalar_one_or_none()
    if not u:
        return RedirectResponse(url="/users", status_code=303)

    tickets_result = await db.execute(select(Ticket).filter(Ticket.created_by_id == u.id).order_by(Ticket.created_at.desc()))
    tickets = tickets_result.scalars().all()

    equipment_result = await db.execute(select(Equipment).filter(Equipment.assigned_to_user_id == u.id).order_by(Equipment.created_at.desc()))
    equipment = equipment_result.scalars().all()

    return templates.TemplateResponse(
        request,
        "user_detail.html",
        {"user": user, "u": u, "tickets": tickets, "equipment": equipment, "UserRole": UserRole},
    )
