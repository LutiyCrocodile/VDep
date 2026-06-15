from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from sqlalchemy import or_, select
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.templates import templates
from app.core.deps import get_current_user, require_role
from app.db.models import Ticket, TicketAttachment, TicketComment, TicketEvent, TicketPriority, TicketStatus, User, UserRole
from app.db.session import get_db

router = APIRouter()


_TICKET_UPLOAD_DIR = Path("app") / "media" / "tickets"
_TICKET_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


TICKET_STATUS_LABELS = {
    TicketStatus.new: "Новая",
    TicketStatus.in_progress: "В работе",
    TicketStatus.waiting_user: "Ожидает пользователя",
    TicketStatus.resolved: "Решена",
    TicketStatus.closed: "Закрыта",
}


TICKET_PRIORITY_LABELS = {
    TicketPriority.low: "Низкий",
    TicketPriority.normal: "Обычный",
    TicketPriority.high: "Высокий",
    TicketPriority.urgent: "Срочно",
    TicketPriority.vip: "VIP",
}


def _max_priority_for_position(position: str | None) -> TicketPriority:
    p = (position or "").strip().lower()
    if not p:
        return TicketPriority.normal

    if "руководитель департамента" in p or p == "руководитель":
        return TicketPriority.vip

    if "зам руководителя департамента" in p:
        return TicketPriority.vip

    if "начальник управления" in p:
        return TicketPriority.urgent

    if "начальник отдела" in p or "зам нач" in p or "зам. нач" in p:
        return TicketPriority.high

    if "советник" in p:
        return TicketPriority.high

    if "ведущий специалист" in p:
        return TicketPriority.high

    if "юрисконсульт" in p:
        return TicketPriority.high

    return TicketPriority.normal


def _allowed_priorities_for_user(user: User) -> list[TicketPriority]:
    order = [TicketPriority.low, TicketPriority.normal, TicketPriority.high, TicketPriority.urgent, TicketPriority.vip]
    max_p = _max_priority_for_position(getattr(user, "position", None))
    allowed: list[TicketPriority] = []
    for v in order:
        allowed.append(v)
        if v == max_p:
            break
    return allowed


def _clamp_priority(user: User, requested: TicketPriority) -> TicketPriority:
    allowed = _allowed_priorities_for_user(user)
    return requested if requested in allowed else allowed[-1]


@router.get("/app", response_class=HTMLResponse)
async def app_home(request: Request, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    view = (request.query_params.get("view") or "queue").strip()
    q = (request.query_params.get("q") or "").strip()
    sort = (request.query_params.get("sort") or "updated_desc").strip()
    sort_by = (request.query_params.get("sort_by") or "").strip()
    sort_dir = (request.query_params.get("dir") or "").strip()
    status_f = (request.query_params.get("status") or "").strip()
    priority_f = (request.query_params.get("priority") or "").strip()
    assignee_f = (request.query_params.get("assignee") or "").strip()

    is_archive = view == "archive"

    if user.role == UserRole.user:
        query = select(Ticket).filter(Ticket.created_by_id == user.id)
    else:
        query = select(Ticket)

    if view == "assigned":
        if user.role == UserRole.user:
            query = query.filter(Ticket.id == -1)
        else:
            query = query.filter(Ticket.assigned_to_id == user.id)

    query = query.options(selectinload(Ticket.created_by), selectinload(Ticket.assigned_to))

    if is_archive:
        query = query.filter(Ticket.status.in_([TicketStatus.resolved, TicketStatus.closed]))
    else:
        query = query.filter(~Ticket.status.in_([TicketStatus.resolved, TicketStatus.closed]))

    if q:
        query = query.filter(or_(Ticket.title.ilike(f"%{q}%"), Ticket.description.ilike(f"%{q}%")))

    if status_f:
        try:
            query = query.filter(Ticket.status == TicketStatus(status_f))
        except Exception:
            status_f = ""

    if priority_f:
        try:
            query = query.filter(Ticket.priority == TicketPriority(priority_f))
        except Exception:
            priority_f = ""

    engineers = []
    if user.role != UserRole.user:
        eng_result = await db.execute(select(User).filter(User.role.in_([UserRole.engineer, UserRole.admin])).order_by(User.username.asc()))
        engineers = eng_result.scalars().all()
        if assignee_f:
            try:
                assignee_id = int(assignee_f)
                query = query.filter(Ticket.assigned_to_id == assignee_id)
            except Exception:
                assignee_f = ""

    if not sort_by:
        if sort == "created_desc":
            sort_by, sort_dir = "created_at", "desc"
        elif sort == "created_asc":
            sort_by, sort_dir = "created_at", "asc"
        elif sort == "updated_asc":
            sort_by, sort_dir = "updated_at", "asc"
        else:
            sort_by, sort_dir = "updated_at", "desc"

    if sort_dir not in ("asc", "desc"):
        sort_dir = "desc"

    sort_map = {
        "id": Ticket.id,
        "title": Ticket.title,
        "status": Ticket.status,
        "priority": Ticket.priority,
        "created_at": Ticket.created_at,
        "updated_at": Ticket.updated_at,
    }
    col = sort_map.get(sort_by, Ticket.updated_at)

    if sort_dir == "asc":
        query = query.order_by(col.asc())
    else:
        query = query.order_by(col.desc())

    result = await db.execute(query)
    tickets = result.scalars().all()

    ctx = {
        "user": user,
        "tickets": tickets,
        "TicketStatus": TicketStatus,
        "TicketPriority": TicketPriority,
        "TICKET_STATUS_LABELS": TICKET_STATUS_LABELS,
        "TICKET_PRIORITY_LABELS": TICKET_PRIORITY_LABELS,
        "view": view,
        "q": q,
        "sort": sort,
        "sort_by": sort_by,
        "dir": sort_dir,
        "status_f": status_f,
        "priority_f": priority_f,
        "assignee_f": assignee_f,
        "engineers": engineers,
    }

    if request.query_params.get("partial") == "1":
        return templates.TemplateResponse(request, "_ticket_list.html", ctx)

    return templates.TemplateResponse(request, "app.html", ctx)


@router.get("/tickets/new", response_class=HTMLResponse)
async def ticket_new_form(request: Request, user: User = Depends(require_role(UserRole.user, UserRole.admin))):
    allowed_priorities = _allowed_priorities_for_user(user)
    return templates.TemplateResponse(
        request,
        "ticket_new.html",
        {
            "user": user,
            "error": None,
            "TicketPriority": TicketPriority,
            "TICKET_PRIORITY_LABELS": TICKET_PRIORITY_LABELS,
            "allowed_priorities": allowed_priorities,
            "title": "",
            "description": "",
            "priority": TicketPriority.normal.value,
        },
    )


@router.get("/tickets/assigned-count", response_class=JSONResponse)
async def assigned_count(
    user: User = Depends(require_role(UserRole.engineer, UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Ticket).filter(
            Ticket.assigned_to_id == user.id,
            ~Ticket.status.in_([TicketStatus.resolved, TicketStatus.closed]),
        )
    )
    count = len(result.scalars().all())
    return {"count": int(count)}


@router.post("/tickets/new")
async def ticket_create(
    request: Request,
    title: str | None = Form(None),
    description: str | None = Form(None),
    priority: TicketPriority = Form(TicketPriority.normal),
    user: User = Depends(require_role(UserRole.user, UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    title_clean = (title or "").strip()
    description_clean = (description or "").strip()
    if not title_clean or not description_clean:
        return templates.TemplateResponse(
            request,
            "ticket_new.html",
            {
                "user": user,
                "error": "Заполните тему и описание.",
                "TicketPriority": TicketPriority,
                "TICKET_PRIORITY_LABELS": TICKET_PRIORITY_LABELS,
                "allowed_priorities": _allowed_priorities_for_user(user),
                "title": title or "",
                "description": description or "",
                "priority": priority.value if hasattr(priority, "value") else str(priority),
            },
            status_code=400,
        )

    effective_priority = _clamp_priority(user, priority)
    t = Ticket(title=title_clean, description=description_clean, priority=effective_priority, created_by_id=user.id)
    db.add(t)
    await db.flush()  # Чтобы получить ID

    db.add(TicketEvent(
        ticket_id=t.id,
        author_id=user.id,
        event_type="created",
        new_value=f"Заявка создана. Приоритет: {TICKET_PRIORITY_LABELS.get(effective_priority)}"
    ))

    await db.commit()
    return RedirectResponse(url="/app", status_code=303)


@router.get("/tickets/{ticket_id}", response_class=HTMLResponse)
async def ticket_detail(ticket_id: int, request: Request, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Ticket).filter(Ticket.id == ticket_id).options(selectinload(Ticket.created_by), selectinload(Ticket.assigned_to)))
    ticket = result.scalar_one_or_none()
    if not ticket:
        return RedirectResponse(url="/app", status_code=303)

    if user.role == UserRole.user and ticket.created_by_id != user.id:
        return RedirectResponse(url="/app", status_code=303)

    comments_result = await db.execute(
        select(TicketComment)
        .filter(TicketComment.ticket_id == ticket.id)
        .order_by(TicketComment.created_at.asc())
    )
    comments = comments_result.scalars().all()

    engineers_result = await db.execute(select(User).filter(User.role.in_([UserRole.engineer, UserRole.admin])).order_by(User.username.asc()))
    engineers = engineers_result.scalars().all()

    attachments_result = await db.execute(
        select(TicketAttachment)
        .filter(TicketAttachment.ticket_id == ticket.id)
        .order_by(TicketAttachment.created_at.asc())
    )
    attachments = attachments_result.scalars().all()

    events_result = await db.execute(
        select(TicketEvent)
        .filter(TicketEvent.ticket_id == ticket.id)
        .order_by(TicketEvent.created_at.desc())
    )
    events = events_result.scalars().all()

    comment_error = request.query_params.get("comment_error")

    return templates.TemplateResponse(
        request,
        "ticket_detail.html",
        {
            "user": user,
            "ticket": ticket,
            "comments": comments,
            "attachments": attachments,
            "events": events,
            "TicketStatus": TicketStatus,
            "TicketPriority": TicketPriority,
            "TICKET_STATUS_LABELS": TICKET_STATUS_LABELS,
            "TICKET_PRIORITY_LABELS": TICKET_PRIORITY_LABELS,
            "engineers": engineers,
            "creator": ticket.created_by,
            "comment_error": comment_error,
        },
    )


@router.post("/tickets/{ticket_id}/attach")
async def attach_image(
    ticket_id: int,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Ticket).filter(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        return RedirectResponse(url="/app", status_code=303)

    if user.role == UserRole.user and ticket.created_by_id != user.id:
        return RedirectResponse(url="/app", status_code=303)

    content_type = (file.content_type or "").lower()
    if content_type not in ("image/jpeg", "image/png", "image/webp"):
        return RedirectResponse(url=f"/tickets/{ticket.id}", status_code=303)

    ext = ".jpg" if content_type == "image/jpeg" else (".png" if content_type == "image/png" else ".webp")
    name = f"{ticket.id}_{uuid4().hex}{ext}"
    dest = _TICKET_UPLOAD_DIR / name
    data = await file.read()
    dest.write_bytes(data)

    rel = f"/media/tickets/{name}"
    db.add(TicketAttachment(ticket_id=ticket.id, uploaded_by_id=user.id, file_path=rel))
    await db.commit()
    return RedirectResponse(url=f"/tickets/{ticket.id}", status_code=303)


@router.post("/tickets/{ticket_id}/resolution")
async def set_resolution(
    ticket_id: int,
    resolution: str | None = Form(None),
    user: User = Depends(require_role(UserRole.engineer, UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Ticket).filter(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        return RedirectResponse(url="/app", status_code=303)

    res_clean = (resolution or "").strip()
    if not res_clean:
        return RedirectResponse(url=f"/tickets/{ticket.id}", status_code=303)

    old_res = ticket.resolution
    ticket.resolution = res_clean
    old_status = ticket.status
    if ticket.status != TicketStatus.closed:
        ticket.status = TicketStatus.resolved

    db.add(TicketEvent(
        ticket_id=ticket.id,
        author_id=user.id,
        event_type="resolution",
        old_value=old_res,
        new_value=res_clean
    ))
    if old_status != ticket.status:
        db.add(TicketEvent(
            ticket_id=ticket.id,
            author_id=user.id,
            event_type="status_change",
            old_value=TICKET_STATUS_LABELS.get(old_status),
            new_value=TICKET_STATUS_LABELS.get(ticket.status)
        ))

    await db.commit()
    return RedirectResponse(url=f"/tickets/{ticket.id}", status_code=303)


@router.post("/tickets/{ticket_id}/comment/{comment_id}/delete")
async def delete_comment(
    ticket_id: int,
    comment_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Ticket).filter(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        return RedirectResponse(url="/app", status_code=303)

    if user.role == UserRole.user and ticket.created_by_id != user.id:
        return RedirectResponse(url="/app", status_code=303)

    comment_result = await db.execute(
        select(TicketComment)
        .filter(TicketComment.id == comment_id, TicketComment.ticket_id == ticket.id)
    )
    comment = comment_result.scalar_one_or_none()
    if not comment:
        return RedirectResponse(url=f"/tickets/{ticket.id}", status_code=303)

    if user.role != UserRole.admin and comment.author_id != user.id:
        return RedirectResponse(url=f"/tickets/{ticket.id}", status_code=303)

    await db.delete(comment)
    await db.commit()
    return RedirectResponse(url=f"/tickets/{ticket.id}", status_code=303)


@router.post("/tickets/{ticket_id}/comment")
async def add_comment(
    ticket_id: int,
    body: str | None = Form(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Ticket).filter(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        return RedirectResponse(url="/app", status_code=303)

    if user.role == UserRole.user and ticket.created_by_id != user.id:
        return RedirectResponse(url="/app", status_code=303)

    body_clean = (body or "").strip()
    if not body_clean:
        return RedirectResponse(url=f"/tickets/{ticket.id}?comment_error=empty", status_code=303)

    db.add(TicketComment(ticket_id=ticket.id, author_id=user.id, body=body_clean))
    
    # Уведомление автору заявки о новом комментарии
    from app.db.models import Notification
    if ticket.created_by_id != user.id:
        author_name = user.full_name or user.username
        db.add(Notification(
            user_id=ticket.created_by_id,
            title=f"Заявка #{ticket.id}: новый комментарий",
            body=f"{author_name}: {body_clean[:100]}{'...' if len(body_clean) > 100 else ''}",
        ))
    
    old_status = ticket.status
    if ticket.status == TicketStatus.waiting_user and user.role != UserRole.user:
        ticket.status = TicketStatus.in_progress
    if ticket.status == TicketStatus.resolved and ticket.status != TicketStatus.closed and user.role == UserRole.user:
        ticket.status = TicketStatus.in_progress
    
    if old_status != ticket.status:
        db.add(TicketEvent(
            ticket_id=ticket.id,
            author_id=user.id,
            event_type="status_change",
            old_value=TICKET_STATUS_LABELS.get(old_status),
            new_value=TICKET_STATUS_LABELS.get(ticket.status)
        ))

    await db.commit()

    return RedirectResponse(url=f"/tickets/{ticket.id}", status_code=303)


@router.post("/tickets/{ticket_id}/status")
async def set_status(
    ticket_id: int,
    status: TicketStatus = Form(...),
    user: User = Depends(require_role(UserRole.engineer, UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Ticket).filter(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        return RedirectResponse(url="/app", status_code=303)

    old_status = ticket.status
    ticket.status = status
    
    if old_status != ticket.status:
        db.add(TicketEvent(
            ticket_id=ticket.id,
            author_id=user.id,
            event_type="status_change",
            old_value=TICKET_STATUS_LABELS.get(old_status),
            new_value=TICKET_STATUS_LABELS.get(ticket.status)
        ))
        
        # Уведомление автору заявки
        from app.db.models import Notification
        if ticket.created_by_id != user.id:
            db.add(Notification(
                user_id=ticket.created_by_id,
                title=f"Заявка #{ticket.id}: изменён статус",
                body=f"Статус изменён на «{TICKET_STATUS_LABELS.get(ticket.status)}»",
            ))

    await db.commit()
    return RedirectResponse(url=f"/tickets/{ticket.id}", status_code=303)


@router.post("/tickets/{ticket_id}/assign")
async def assign_ticket(
    ticket_id: int,
    assigned_to_id: str | None = Form(None),
    user: User = Depends(require_role(UserRole.engineer, UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Ticket).filter(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        return RedirectResponse(url="/app", status_code=303)

    old_assignee_id = ticket.assigned_to_id
    old_assignee_u = ticket.assigned_to.username if ticket.assigned_to else "—"
    old_status = ticket.status

    assignee = None
    if assigned_to_id:
        assignee_result = await db.execute(select(User).filter(User.id == assigned_to_id))
        assignee = assignee_result.scalar_one_or_none()
        if not assignee or assignee.role not in (UserRole.engineer, UserRole.admin):
            return RedirectResponse(url=f"/tickets/{ticket.id}", status_code=303)
        ticket.assigned_to_id = assignee.id
        if ticket.status == TicketStatus.new:
            ticket.status = TicketStatus.in_progress
        
        new_assignee_u = assignee.username
    else:
        ticket.assigned_to_id = None
        new_assignee_u = "—"

    if old_assignee_id != ticket.assigned_to_id:
        db.add(TicketEvent(
            ticket_id=ticket.id,
            author_id=user.id,
            event_type="assigned",
            old_value=old_assignee_u,
            new_value=new_assignee_u
        ))
        
        # Уведомление автору заявки
        from app.db.models import Notification
        if ticket.created_by_id != user.id:
            if assigned_to_id:
                assignee_name = assignee.full_name or assignee.username
                db.add(Notification(
                    user_id=ticket.created_by_id,
                    title=f"Заявка #{ticket.id}: назначен инженер",
                    body=f"Ваша заявка назначена инженеру {assignee_name}",
                ))
        
        # Уведомление инженеру при назначении на него
        if assigned_to_id and assignee.id != user.id:
            assigner_name = user.full_name or user.username
            db.add(Notification(
                user_id=assignee.id,
                title=f"Заявка #{ticket.id}: назначена на вас",
                body=f"{assigner_name} назначил заявку на вас",
            ))
    
    if old_status != ticket.status:
        db.add(TicketEvent(
            ticket_id=ticket.id,
            author_id=user.id,
            event_type="status_change",
            old_value=TICKET_STATUS_LABELS.get(old_status),
            new_value=TICKET_STATUS_LABELS.get(ticket.status)
        ))
        
        # Уведомление автору заявки
        from app.db.models import Notification
        if ticket.created_by_id != user.id:
            db.add(Notification(
                user_id=ticket.created_by_id,
                title=f"Заявка #{ticket.id}: изменён статус",
                body=f"Статус изменён на «{TICKET_STATUS_LABELS.get(ticket.status)}»",
            ))

    await db.commit()
    return RedirectResponse(url=f"/tickets/{ticket.id}", status_code=303)
