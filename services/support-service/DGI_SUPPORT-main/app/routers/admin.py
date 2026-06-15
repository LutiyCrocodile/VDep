from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.templates import templates
from app.core.deps import require_role, get_current_user_optional
from app.core.security import hash_password
from app.routers.auth import _validate_password, _RE_USERNAME
from app.db.models import User, UserRole
from app.db.session import get_db
from app.core.auth_client import auth_client

router = APIRouter(prefix="/admin")


@router.get("/pending-badge", response_class=HTMLResponse)
async def pending_badge(
    request: Request,
    user: User = Depends(require_role(UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).filter(User.needs_approval == True))
    count = len(result.scalars().all())
    if count <= 0:
        return "<span id=\"pendingRegBadge\" class=\"hidden\"></span>"
    return (
        "<span id=\"pendingRegBadge\" class=\"ml-2 inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-rose-600 px-1 text-xs font-semibold text-white ring-1 ring-rose-400/30\">"
        + str(count)
        + "</span>"
    )


@router.get("/pending-count", response_class=JSONResponse)
async def pending_count(
    user: User = Depends(require_role(UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).filter(User.needs_approval == True))
    count = len(result.scalars().all())
    return {"count": int(count)}


@router.get("/users", response_class=HTMLResponse)
async def users_list(
    request: Request,
    user: User = Depends(require_role(UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    return templates.TemplateResponse(
        request,
        "admin_users.html",
        {"user": user, "users": users, "UserRole": UserRole, "error": request.query_params.get("error")},
    )


@router.get("/users/new", response_class=HTMLResponse)
async def user_create_form(
    request: Request,
    user: User = Depends(require_role(UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    # Get services for role selection
    services = await auth_client.get_services()

    # Get positions sorted by priority
    from app.db.models import Position
    positions_result = await db.execute(select(Position).order_by(Position.sort_order))
    positions = positions_result.scalars().all()

    return templates.TemplateResponse(
        request,
        "admin_user_new.html",
        {"user": user, "u": None, "UserRole": UserRole, "services": services, "positions": positions},
    )


@router.get("/users/{user_id}/edit", response_class=HTMLResponse)
async def user_edit_form(
    user_id: str,
    request: Request,
    user: User = Depends(require_role(UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    import uuid as uuid_mod
    try:
        user_uuid = uuid_mod.UUID(user_id)
    except ValueError:
        return RedirectResponse(url="/admin/users", status_code=303)
    result = await db.execute(select(User).filter(User.id == user_uuid))
    u = result.scalar_one_or_none()
    if not u:
        return RedirectResponse(url="/admin/users", status_code=303)

    # Get services and user's current roles
    services = await auth_client.get_services()
    user_service_access = await auth_client.get_all_service_access(str(u.id))

    # Add current role to each service
    for service in services:
        service["current_role"] = None
        if user_service_access and user_service_access.get("services"):
            for svc_slug, svc_data in user_service_access["services"].items():
                if svc_slug == service["slug"]:
                    service["current_role"] = svc_data.get("role")
                    break

    # Get positions sorted by priority
    from app.db.models import Position
    positions_result = await db.execute(select(Position).order_by(Position.sort_order))
    positions = positions_result.scalars().all()

    # Get user data from auth-service (including email)
    auth_user_data = await auth_client.get_user_profile_internal(str(u.id))
    user_email = auth_user_data.get("email") if auth_user_data else None

    return templates.TemplateResponse(
        request,
        "admin_user_new.html",
        {"user": user, "u": u, "UserRole": UserRole, "services": services, "user_email": user_email, "positions": positions},
    )


@router.post("/users/create")
async def user_create(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(""),
    position_id: str = Form(""),
    internal_number: str = Form(""),
    office: str = Form(""),
    is_active: str = Form("1"),
    role: str = Form("user"),
    user: User = Depends(require_role(UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    import uuid as uuid_mod
    import logging
    logger = logging.getLogger(__name__)

    # Validate username
    if not _RE_USERNAME.match(username):
        logger.warning(f"Username validation failed: {username}")
        return RedirectResponse(url="/admin/users?error=username_format", status_code=303)

    # Validate password
    if not _validate_password(password):
        logger.warning(f"Password validation failed for user: {username}")
        return RedirectResponse(url="/admin/users?error=password_weak", status_code=303)

    # Create user in auth-service
    logger.info(f"Creating user in auth-service: {username}, {email}")
    status, auth_user_data = await auth_client.create_user_internal(
        username=username,
        email=email,
        password=password,
        full_name=full_name or None,
        role=role,
        is_employee=True,
    )
    logger.info(f"Auth-service response: status={status}, data={auth_user_data}")

    if status != 200 or not auth_user_data:
        logger.error(f"Failed to create user in auth-service: status={status}")
        # Check for specific errors
        if status == 400:
            error_detail = ""
            if isinstance(auth_user_data, dict):
                error_detail = str(auth_user_data.get("detail", ""))
            elif auth_user_data:
                error_detail = str(auth_user_data)
            if "Password must be at least 8 characters" in error_detail:
                return RedirectResponse(url="/admin/users/new?error=password_too_short", status_code=303)
            if "Email already exists" in error_detail:
                return RedirectResponse(url="/admin/users/new?error=email_exists", status_code=303)
            if "Username already exists" in error_detail:
                return RedirectResponse(url="/admin/users/new?error=exists", status_code=303)
            # Pass the actual error message
            return RedirectResponse(url=f"/admin/users/new?error={error_detail}", status_code=303)
        return RedirectResponse(url="/admin/users/new?error=create_failed", status_code=303)

    # Create local user profile
    user_uuid = uuid_mod.UUID(auth_user_data["id"])

    # Get position name if position_id is provided
    position_name = None
    if position_id:
        from app.db.models import Position
        pos_result = await db.execute(select(Position).filter(Position.id == int(position_id)))
        position_obj = pos_result.scalar_one_or_none()
        if position_obj:
            position_name = position_obj.name

    new_user = User(
        id=user_uuid,
        username=username,
        full_name=full_name or username,
        role=role,
        is_active=is_active == "1",
        needs_approval=False,
        position=position_name,  # Keep for backward compatibility
        position_id=int(position_id) if position_id else None,
        internal_number=internal_number,
        office=office,
    )
    db.add(new_user)
    await db.commit()
    logger.info(f"User created successfully: {username}")

    # Assign service roles
    form_data = await request.form()
    services = await auth_client.get_services()
    for service in services:
        service_slug = service["slug"]
        role_key = f"service_role_{service_slug}"
        new_role = form_data.get(role_key, "")
        if new_role:
            logger.info(f"Assigning role {new_role} to user {user_uuid} for service {service_slug}")
            await auth_client.assign_service_role(str(user_uuid), service_slug, new_role)

    return RedirectResponse(url="/admin/users", status_code=303)


@router.post("/users/{user_id}/approve")
async def user_approve(
    user_id: str,
    user: User = Depends(require_role(UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    import uuid as uuid_mod
    try:
        user_uuid = uuid_mod.UUID(user_id)
    except ValueError:
        return RedirectResponse(url="/admin/users", status_code=303)
    result = await db.execute(select(User).filter(User.id == user_uuid))
    u = result.scalar_one_or_none()
    if not u:
        return RedirectResponse(url="/admin/users", status_code=303)
    u.is_active = True
    u.needs_approval = False
    await db.commit()
    return RedirectResponse(url="/admin/users", status_code=303)


@router.post("/users/{user_id}/reject")
async def user_reject(
    user_id: str,
    user: User = Depends(require_role(UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    import uuid as uuid_mod
    try:
        user_uuid = uuid_mod.UUID(user_id)
    except ValueError:
        return RedirectResponse(url="/admin/users", status_code=303)
    result = await db.execute(select(User).filter(User.id == user_uuid))
    u = result.scalar_one_or_none()
    if not u:
        return RedirectResponse(url="/admin/users", status_code=303)
    if not u.needs_approval:
        return RedirectResponse(url="/admin/users", status_code=303)
    await db.delete(u)
    await db.commit()
    return RedirectResponse(url="/admin/users", status_code=303)


@router.post("/users/{user_id}/delete")
async def user_delete(
    user_id: str,
    user: User = Depends(require_role(UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    import uuid as uuid_mod
    try:
        user_uuid = uuid_mod.UUID(user_id)
    except ValueError:
        return RedirectResponse(url="/admin/users", status_code=303)
    result = await db.execute(select(User).filter(User.id == user_uuid))
    u = result.scalar_one_or_none()
    if not u:
        return RedirectResponse(url="/admin/users", status_code=303)
    if u.id == user.id:
        return RedirectResponse(url="/admin/users", status_code=303)

    # Soft delete in auth-service
    await auth_client.delete_user_internal(str(user_uuid))

    # Delete local user profile
    await db.delete(u)
    await db.commit()
    return RedirectResponse(url="/admin/users", status_code=303)


@router.post("/users/{user_id}/update")
async def user_update(
    request: Request,
    user_id: str,
    username: str = Form(""),
    email: str = Form(""),
    is_active: int = Form(...),
    full_name: str = Form(""),
    position_id: str = Form(""),
    internal_number: str = Form(""),
    office: str = Form(""),
    password: str = Form(""),
    user: User = Depends(require_role(UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    import uuid as uuid_mod
    import logging
    logger = logging.getLogger(__name__)

    try:
        user_uuid = uuid_mod.UUID(user_id)
    except ValueError:
        logger.warning(f"Invalid UUID format: {user_id}")
        return RedirectResponse(url="/admin/users", status_code=303)
    result = await db.execute(select(User).filter(User.id == user_uuid))
    u = result.scalar_one_or_none()
    if not u:
        logger.warning(f"User not found: {user_id}")
        return RedirectResponse(url="/admin/users", status_code=303)

    # Update local fields
    if username and username != u.username:
        u.username = username
    u.is_active = bool(int(is_active))
    u.full_name = (full_name or None)
    u.internal_number = (internal_number or None)
    u.office = (office or None)

    # Update position
    if position_id:
        from app.db.models import Position
        pos_result = await db.execute(select(Position).filter(Position.id == int(position_id)))
        position_obj = pos_result.scalar_one_or_none()
        if position_obj:
            u.position = position_obj.name  # Keep for backward compatibility
            u.position_id = int(position_id)
    else:
        u.position = None
        u.position_id = None

    await db.commit()
    logger.info(f"Local user updated: {user_id}, username={username}, email={email}, is_active={u.is_active}")

    # Sync with auth-service (without global role)
    logger.info(f"Syncing with auth-service: {user_id}")
    await auth_client.update_user_internal(
        user_id=str(user_uuid),
        username=username if username and username != u.username else None,
        email=email if email and email.strip() else None,
        full_name=full_name or None,
        is_active=bool(int(is_active)),
        password=password if password and password.strip() else None,
    )
    logger.info(f"Auth-service sync completed for: {user_id}")

    # Update service roles
    form_data = await request.form()
    services = await auth_client.get_services()
    for service in services:
        service_slug = service["slug"]
        role_key = f"service_role_{service_slug}"
        new_role = form_data.get(role_key, "")
        if new_role:
            logger.info(f"Assigning role {new_role} to user {user_id} for service {service_slug}")
            await auth_client.assign_service_role(str(user_uuid), service_slug, new_role)
        else:
            # If role is empty (no access), remove the service role
            logger.info(f"Removing role for user {user_id} from service {service_slug}")
            await auth_client.assign_service_role(str(user_uuid), service_slug, "")

    return RedirectResponse(url="/admin/users", status_code=303)


@router.get("/seed")
@router.post("/seed")
async def seed_database(
    user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """Fill database with test data (users, tickets, equipment, KB, notifications)."""
    # Temporarily allow without auth for initial setup
    # TODO: Re-enable auth check after initial deployment

    from app.db.models import (
        User, UserRole, Ticket, TicketStatus, TicketPriority,
        TicketComment, TicketEvent, TicketAttachment, Equipment,
        EquipmentCategory, EquipmentStatus, ConsumableType,
        KbArticle, KbFile, KbCategory, Notification, Broadcast
    )
    from datetime import datetime, timedelta
    from random import randint
    import uuid as uuid_mod

    # Wipe existing data
    notif_result = await db.execute(select(Notification))
    for n in notif_result.scalars().all():
        await db.delete(n)
    
    broadcast_result = await db.execute(select(Broadcast))
    for b in broadcast_result.scalars().all():
        await db.delete(b)
    
    attach_result = await db.execute(select(TicketAttachment))
    for t in attach_result.scalars().all():
        await db.delete(t)
    
    comment_result = await db.execute(select(TicketComment))
    for c in comment_result.scalars().all():
        await db.delete(c)
    
    event_result = await db.execute(select(TicketEvent))
    for e in event_result.scalars().all():
        await db.delete(e)
    
    ticket_result = await db.execute(select(Ticket))
    for t in ticket_result.scalars().all():
        await db.delete(t)
    
    eq_result = await db.execute(select(Equipment))
    for e in eq_result.scalars().all():
        await db.delete(e)
    
    kbfile_result = await db.execute(select(KbFile))
    for k in kbfile_result.scalars().all():
        await db.delete(k)
    
    kbart_result = await db.execute(select(KbArticle))
    for k in kbart_result.scalars().all():
        await db.delete(k)
    
    user_result = await db.execute(select(User))
    for u in user_result.scalars().all():
        await db.delete(u)
    
    await db.commit()

    # Accounts
    ACCOUNTS = [
        ("EvteevAS",    "Евтеев А.С.",   "Администратор системы",             UserRole.admin,   "21-001", "18.01"),
        ("KozlovDV",    "Козлов Д.В.",   "Инженер техподдержки",              UserRole.engineer, "21-010", "18.05"),
        ("PetrovaEM",   "Петрова Е.М.",  "Инженер техподдержки",              UserRole.engineer, "21-011", "18.06"),
        ("SidorovNA",   "Сидоров Н.А.",  "Старший инженер техподдержки",      UserRole.engineer, "21-012", "18.07"),
        ("KarpovVI",    "Карпов В.И.",   "Руководитель департамента",         UserRole.user,     "21-000", "01.01"),
        ("OrlovaNS",    "Орлова Н.С.",   "Зам руководителя департамента",     UserRole.user,     "21-001", "01.02"),
        ("MikhailovKT", "Михайлов К.Т.", "Начальник управления приватизации", UserRole.user,     "22-001", "12.01"),
        ("ZaitsevaOP",  "Зайцева О.П.",  "Начальник управления аренды",      UserRole.user,     "22-002", "14.01"),
        ("KrylovaDA",   "Крылова Д.А.",  "Начальник управления земельных участков", UserRole.user, "22-003", "10.01"),
        ("BelyaevGS",   "Беляев Г.С.",   "Начальник управления госуслуг",    UserRole.user,     "22-004", "22.01"),
        ("RomanovaEV",  "Романова Е.В.", "Начальник управления КРТ",          UserRole.user,     "22-005", "24.01"),
        ("FedorovRS",   "Фёдоров Р.С.",  "Начальник отдела земель ЦАО",      UserRole.user,     "22-400", "20.10"),
        ("LebedevAP",   "Лебедев А.П.",  "Начальник отдела приватизации нежилых", UserRole.user, "22-410", "12.10"),
        ("SokolovaIM",  "Соколова И.М.", "Зам начальника управления аренды", UserRole.user,     "22-020", "14.05"),
        ("IvanovMP",    "Иванов М.П.",   "Ведущий специалист управления приватизации",  UserRole.user, "22-100", "12.02"),
        ("VolkovIG",    "Волков И.Г.",   "Ведущий специалист управления аренды", UserRole.user,  "22-200", "14.03"),
        ("MorozovAP",   "Морозов А.П.",  "Ведущий специалист управления КРТ", UserRole.user,     "22-700", "24.02"),
        ("SmirnovaOV",  "Смирнова О.В.", "Специалист управления приватизации", UserRole.user,     "22-101", "12.03"),
        ("NovikovaAT",  "Новикова А.Т.", "Юрисконсульт управления аренды",    UserRole.user,     "22-300", "16.01"),
        ("KuznetsovaLB","Кузнецова Л.Б.","Специалист управления земельных участков", UserRole.user, "22-500", "10.02"),
        ("BelovaNK",    "Белова Н.К.",   "Специалист управления госуслуг",    UserRole.user,     "22-600", "22.03"),
    ]

    for username, full_name, position, role, int_num, office in ACCOUNTS:
        db.add(User(
            id=uuid_mod.uuid4(),
            username=username,
            full_name=full_name,
            position=position,
            role=role,
            internal_number=int_num,
            office=office,
            is_active=True,
        ))
    await db.commit()

    # KB articles
    admin_result = await db.execute(select(User).filter(User.username == "EvteevAS"))
    admin_user = admin_result.scalar_one()
    faq_articles = [
        KbArticle(title="Как сменить пароль", body="Зайдите в профиль и нажмите 'Сменить пароль'.", category=KbCategory.faq, is_published=True, author_id=admin_user.id),
        KbArticle(title="Как создать заявку", body="Нажмите 'Новая заявка' и заполните форму.", category=KbCategory.faq, is_published=True, author_id=admin_user.id),
        KbArticle(title="Как подключить принтер", body="Настройки -> Устройства -> Добавить принтер.", category=KbCategory.guide, is_published=True, author_id=admin_user.id),
        KbArticle(title="Политика безопасности", body="Пароль должен быть не менее 8 символов с заглавной буквой и цифрой.", category=KbCategory.policy, is_published=True, author_id=admin_user.id),
        KbArticle(title="Порядок выдачи оборудования", body="Оборудование выдаётся по заявке через инженера.", category=KbCategory.policy, is_published=True, author_id=admin_user.id),
    ]
    for art in faq_articles:
        db.add(art)
    await db.commit()

    # Equipment
    EC = EquipmentCategory
    ES = EquipmentStatus
    CT = ConsumableType

    # Monoblocks assigned to users
    office_users = {
        "18.01": ["EvteevAS"],
        "18.05": ["KozlovDV"],
        "18.06": ["PetrovaEM"],
        "18.07": ["SidorovNA"],
        "01.01": ["KarpovVI"],
        "01.02": ["OrlovaNS"],
        "12.01": ["MikhailovKT"],
        "14.01": ["ZaitsevaOP"],
        "10.01": ["KrylovaDA"],
        "22.01": ["BelyaevGS"],
        "24.01": ["RomanovaEV"],
        "20.10": ["FedorovRS"],
        "12.10": ["LebedevAP"],
        "14.05": ["SokolovaIM"],
        "12.02": ["IvanovMP"],
        "14.03": ["VolkovIG"],
        "24.02": ["MorozovAP"],
        "12.03": ["SmirnovaOV"],
        "16.01": ["NovikovaAT"],
        "10.02": ["KuznetsovaLB"],
        "22.03": ["BelovaNK"],
    }

    for office, usernames in office_users.items():
        for username in usernames:
            u_result = await db.execute(select(User).filter(User.username == username))
            u = u_result.scalar_one_or_none()
            if u:
                db.add(Equipment(
                    category=EC.monoblock,
                    model="HP EliteOne 800 G6",
                    serial_number=f"CZC{randint(100000, 999999)}",
                    name=f"Моноблок HP EliteOne 800 G6",
                    status=ES.assigned,
                    assigned_to_user_id=u.id,
                    location=office,
                    is_warehouse=False,
                ))

    # Warehouse monoblocks
    for i in range(5):
        db.add(Equipment(
            category=EC.monoblock,
            model="HP EliteOne 800 G6",
            serial_number=f"CZC{randint(100000, 999999)}",
            name=f"Моноблок HP EliteOne 800 G6 (склад)",
            status=ES.in_stock,
            location="Склад",
            is_warehouse=True,
        ))

    # Printers
    printer_models = [
        ("HP LaserJet M404dn", "18.05"),
        ("HP MFP 4101", "14.01"),
        ("HP Color LaserJet 3301", "22.01"),
        ("Kyocera ECOSYS P2235", "10.01"),
    ]
    for model, loc in printer_models:
        db.add(Equipment(
            category=EC.printer,
            model=model,
            serial_number=f"VNC{randint(100000, 999999)}",
            name=f"Принтер {model}",
            status=ES.in_stock,
            location=loc,
            is_warehouse=True,
        ))

    # Consumables
    cartridge_stock = [
        ("Картридж HP 26A (CF226A)", "HP LaserJet M404/M428", 15),
        ("Картридж HP 32A (CF232A)", "HP MFP 4101", 10),
        ("Картридж HP 134A (W1340A)", "HP Color LaserJet 3301 чёрный", 8),
        ("Картридж HP 134A (W1341C)", "HP Color LaserJet 3301 голубой", 5),
        ("Картридж HP 134A (W1342M)", "HP Color LaserJet 3301 пурпурный", 5),
        ("Картридж HP 134A (W1343Y)", "HP Color LaserJet 3301 жёлтый", 5),
        ("Картридж Kyocera TK-2235", "Kyocera ECOSYS P2235", 8),
    ]
    for name, model, qty in cartridge_stock:
        db.add(Equipment(
            category=EC.consumable,
            consumable_type=CT.cartridge,
            model=model,
            name=name,
            status=ES.in_stock,
            location="Склад",
            is_warehouse=True,
            notes=f"Количество: {qty} шт." if qty > 1 else None,
        ))

    consumable_stock = [
        ("Мышь проводная HP USB", None, CT.peripheral, 20),
        ("Мышь беспроводная HP", None, CT.peripheral, 10),
        ("Клавиатура HP USB", None, CT.peripheral, 15),
        ("Клавиатура беспроводная HP", None, CT.peripheral, 8),
        ("Кабель HDMI 1.5м", None, CT.cable, 12),
        ("Кабель DisplayPort 1.5м", None, CT.cable, 10),
        ("Кабель USB-C 1м", None, CT.cable, 15),
        ("Блок питания HP 65Вт", None, CT.accessory, 6),
        ("Веб-камера HP USB", None, CT.accessory, 4),
        ("Наушники с микрофоном", None, CT.accessory, 5),
    ]
    for name, model, ctype, qty in consumable_stock:
        db.add(Equipment(
            category=EC.consumable,
            consumable_type=ctype,
            model=model,
            name=name,
            status=ES.in_stock,
            location="Склад",
            is_warehouse=True,
            notes=f"Количество: {qty} шт." if qty > 1 else None,
        ))

    await db.commit()

    # Tickets with history
    all_users_result = await db.execute(select(User))
    all_users = all_users_result.scalars().all()
    engineers_result = await db.execute(select(User).filter(User.role == UserRole.engineer))
    engineers = engineers_result.scalars().all()

    for i in range(24):
        creator = all_users[randint(0, len(all_users)-1)]
        engineer = engineers[randint(0, len(engineers)-1)]
        ticket = Ticket(
            title=f"Заявка #{i+1}: Проблема с компьютером",
            description="Компьютер не включается. Нужна помощь инженера.",
            status=TicketStatus.new if i % 3 == 0 else (TicketStatus.in_progress if i % 3 == 1 else TicketStatus.resolved),
            priority=TicketPriority.high if i % 5 == 0 else TicketPriority.normal,
            created_by_id=creator.id,
            assigned_to_id=engineer.id if i % 2 == 0 else None,
        )
        db.add(ticket)
        await db.flush()

        # Add events
        if i % 2 == 0:
            db.add(TicketEvent(
                ticket_id=ticket.id,
                author_id=engineer.id,
                event_type="assigned",
                new_value=str(engineer.id),
            ))
        if i % 3 == 2:
            db.add(TicketEvent(
                ticket_id=ticket.id,
                author_id=engineer.id,
                event_type="status_changed",
                old_value="new",
                new_value="resolved",
            ))

    await db.commit()

    # Broadcasts and notifications
    broadcasts = [
        ("Обновление системы", "Система техподдержки обновлена. Теперь есть новые функции."),
        ("Плановое обслуживание", "Плановое обслуживание серверов в выходные."),
        ("Новые инструкции", "Добавлены новые инструкции в базу знаний."),
        ("Смена паролей", "Рекомендуется сменить пароли раз в 3 месяца."),
    ]
    for title, body in broadcasts:
        b = Broadcast(title=title, body=body, author_id=admin_user.id)
        db.add(b)
        await db.flush()
        # Notify all users
        for u in all_users:
            db.add(Notification(
                user_id=u.id,
                title=title,
                body=body,
                broadcast_id=b.id,
            ))

    await db.commit()

    return RedirectResponse(url="/admin/users", status_code=303)
