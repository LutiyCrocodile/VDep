from __future__ import annotations

from sqlalchemy import and_, not_, or_, select
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.templates import templates
from app.core.deps import require_role
from app.db.models import ConsumableType, Equipment, EquipmentCategory, EquipmentStatus, User, UserRole
from app.db.session import get_db

router = APIRouter(prefix="/equipment")


EQUIPMENT_STATUS_LABELS = {
    EquipmentStatus.in_stock: "На складе",
    EquipmentStatus.assigned: "Выдано",
    EquipmentStatus.retired: "Списано",
}

EQUIPMENT_CATEGORY_LABELS = {
    EquipmentCategory.monoblock: "Моноблоки",
    EquipmentCategory.printer: "Принтеры",
    EquipmentCategory.consumable: "Расходные материалы",
}

CONSUMABLE_TYPE_LABELS = {
    ConsumableType.cartridge: "Картриджи",
    ConsumableType.peripheral: "Периферия",
    ConsumableType.cable: "Кабели",
    ConsumableType.accessory: "Аксессуары",
}


@router.get("", response_class=HTMLResponse)
async def equipment_list(
    request: Request,
    user: User = Depends(require_role(UserRole.engineer, UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    view = (request.query_params.get("view") or "all").strip()
    q = (request.query_params.get("q") or "").strip()
    sort = (request.query_params.get("sort") or "name_asc").strip()
    cat_f = (request.query_params.get("category") or "").strip()
    model_f = (request.query_params.get("model") or "").strip()
    location_f = (request.query_params.get("location") or "").strip()
    user_f = (request.query_params.get("user") or "").strip()
    ctype_f = (request.query_params.get("consumable_type") or "").strip()
    err = (request.query_params.get("err") or "").strip()

    # Resolve user filter: text search by full_name/username
    user_name_f = user_f
    matched_user_ids = None
    if user_f:
        result = await db.execute(
            select(User).filter(
                or_(User.full_name.ilike(f"%{user_f}%"), User.username.ilike(f"%{user_f}%"))
            )
        )
        matched = result.scalars().all()
        matched_user_ids = [u.id for u in matched] if matched else [-1]  # -1 = no match
        user_name_f = user_f

    query = select(Equipment)

    if view == "warehouse":
        query = query.filter(Equipment.is_warehouse == True)
    elif view == "assigned":
        query = query.filter(Equipment.status == EquipmentStatus.assigned)
    elif view == "retired":
        query = query.filter(Equipment.status == EquipmentStatus.retired)
    else:
        pass  # all

    if cat_f:
        try:
            query = query.filter(Equipment.category == EquipmentCategory(cat_f))
        except Exception:
            cat_f = ""

    if ctype_f:
        try:
            query = query.filter(Equipment.consumable_type == ConsumableType(ctype_f))
        except Exception:
            ctype_f = ""

    if model_f:
        query = query.filter(Equipment.model.ilike(f"%{model_f}%"))

    if location_f:
        query = query.filter(Equipment.location.ilike(f"%{location_f}%"))

    if matched_user_ids is not None:
        query = query.filter(Equipment.assigned_to_user_id.in_(matched_user_ids))

    if q:
        query = query.filter(
            or_(
                Equipment.serial_number.ilike(f"%{q}%"),
                Equipment.name.ilike(f"%{q}%"),
                Equipment.model.ilike(f"%{q}%"),
                Equipment.notes.ilike(f"%{q}%"),
                Equipment.location.ilike(f"%{q}%"),
            )
        )

    if sort == "created_asc":
        query = query.order_by(Equipment.created_at.asc())
    elif sort == "location_asc":
        query = query.order_by(Equipment.location.asc())
    else:
        query = query.order_by(Equipment.name.asc())

    result = await db.execute(query)
    items = result.scalars().all()
    
    users_result = await db.execute(select(User).order_by(User.full_name.asc(), User.username.asc()))
    users = users_result.scalars().all()

    # Build user lookup for display
    user_map = {u.id: u for u in users}

    # Collect unique models and locations for filter dropdowns
    all_eq_result = await db.execute(select(Equipment))
    all_eq = all_eq_result.scalars().all()
    all_models = sorted(set(it.model for it in all_eq if it.model))
    all_locations = sorted(set(it.location for it in all_eq if it.location))

    return templates.TemplateResponse(
        request,
        "equipment.html",
        {
            "user": user,
            "items": items,
            "users": users,
            "user_map": user_map,
            "EquipmentStatus": EquipmentStatus,
            "EquipmentCategory": EquipmentCategory,
            "EQUIPMENT_STATUS_LABELS": EQUIPMENT_STATUS_LABELS,
            "EQUIPMENT_CATEGORY_LABELS": EQUIPMENT_CATEGORY_LABELS,
            "view": view,
            "q": q,
            "sort": sort,
            "cat_f": cat_f,
            "model_f": model_f,
            "location_f": location_f,
            "user_f": user_f,
            "user_name_f": user_name_f,
            "ctype_f": ctype_f,
            "ConsumableType": ConsumableType,
            "CONSUMABLE_TYPE_LABELS": CONSUMABLE_TYPE_LABELS,
            "all_models": all_models,
            "all_locations": all_locations,
            "err": err,
        },
    )


@router.get("/new", response_class=HTMLResponse)
async def equipment_new_form(
    request: Request,
    user: User = Depends(require_role(UserRole.engineer, UserRole.admin)),
):
    return templates.TemplateResponse(
        request,
        "admin_equipment_new.html",
        {
            "user": user,
            "EquipmentCategory": EquipmentCategory,
            "EquipmentStatus": EquipmentStatus,
            "ConsumableType": ConsumableType,
            "EQUIPMENT_STATUS_LABELS": EQUIPMENT_STATUS_LABELS,
            "EQUIPMENT_CATEGORY_LABELS": EQUIPMENT_CATEGORY_LABELS,
            "CONSUMABLE_TYPE_LABELS": CONSUMABLE_TYPE_LABELS,
        },
    )


@router.get("/{equipment_id}", response_class=HTMLResponse)
async def equipment_detail(
    equipment_id: int,
    request: Request,
    user: User = Depends(require_role(UserRole.engineer, UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Equipment).filter(Equipment.id == equipment_id))
    item = result.scalar_one_or_none()
    if not item:
        return RedirectResponse(url="/equipment", status_code=303)

    assigned_user = None
    if item.assigned_to_user_id:
        user_result = await db.execute(select(User).filter(User.id == item.assigned_to_user_id))
        assigned_user = user_result.scalar_one_or_none()

    users_result = await db.execute(select(User).order_by(User.full_name.asc(), User.username.asc()))
    users = users_result.scalars().all()

    return templates.TemplateResponse(
        request,
        "equipment_detail.html",
        {
            "user": user,
            "item": item,
            "assigned_user": assigned_user,
            "users": users,
            "EquipmentCategory": EquipmentCategory,
            "EquipmentStatus": EquipmentStatus,
            "ConsumableType": ConsumableType,
            "EQUIPMENT_STATUS_LABELS": EQUIPMENT_STATUS_LABELS,
            "EQUIPMENT_CATEGORY_LABELS": EQUIPMENT_CATEGORY_LABELS,
            "CONSUMABLE_TYPE_LABELS": CONSUMABLE_TYPE_LABELS,
        },
    )


@router.post("/new")
async def equipment_create(
    category: EquipmentCategory = Form(EquipmentCategory.monoblock),
    status: EquipmentStatus = Form(EquipmentStatus.in_stock),
    consumable_type: str = Form(""),
    model: str = Form(""),
    serial_number: str = Form(""),
    name: str = Form(""),
    location: str = Form(""),
    notes: str = Form(""),
    user: User = Depends(require_role(UserRole.engineer, UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    name = name.strip()
    if not name:
        return RedirectResponse(url="/equipment?err=required", status_code=303)

    ct = None
    if consumable_type:
        try:
            ct = ConsumableType(consumable_type)
        except Exception:
            pass

    sn = serial_number.strip() or None
    # Set is_warehouse based on status
    is_warehouse = status == EquipmentStatus.in_stock
    # If on warehouse, clear location
    loc = location.strip() if not is_warehouse else None
    
    db.add(
        Equipment(
            category=category,
            status=status,
            consumable_type=ct,
            model=(model.strip() or None),
            serial_number=sn,
            name=name,
            location=loc,
            is_warehouse=is_warehouse,
            notes=(notes.strip() or None),
        )
    )
    await db.commit()
    # Get last inserted equipment to redirect to detail
    last_result = await db.execute(select(Equipment).order_by(Equipment.id.desc()).limit(1))
    last = last_result.scalar_one_or_none()
    if last:
        return RedirectResponse(url=f"/equipment/{last.id}", status_code=303)
    return RedirectResponse(url="/equipment", status_code=303)


@router.post("/{equipment_id}/update")
async def equipment_update(
    equipment_id: int,
    status: EquipmentStatus = Form(...),
    category: EquipmentCategory = Form(...),
    consumable_type: str = Form(""),
    model: str = Form(""),
    serial_number: str = Form(""),
    name: str = Form(""),
    assigned_to_user_id: str | None = Form(None),
    location: str = Form(""),
    notes: str = Form(""),
    user: User = Depends(require_role(UserRole.engineer, UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Equipment).filter(Equipment.id == equipment_id))
    item = result.scalar_one_or_none()
    if not item:
        return RedirectResponse(url="/equipment", status_code=303)

    ct = None
    if consumable_type:
        try:
            ct = ConsumableType(consumable_type)
        except Exception:
            pass

    item.category = category
    item.consumable_type = ct
    item.model = (model.strip() or None)
    item.serial_number = (serial_number.strip() or None)
    item.name = (name.strip() or None)
    item.assigned_to_user_id = assigned_to_user_id or None
    item.notes = (notes.strip() or None)
    
    # Consumables: when assigned to user, mark as retired (written off)
    if item.category == EquipmentCategory.consumable and assigned_to_user_id:
        item.status = EquipmentStatus.retired
        item.is_warehouse = False
        if not item.notes:
            item.notes = f"Выдано сотруднику"
    else:
        # Use status from form for all other cases
        item.status = status
        # Set is_warehouse based on status
        item.is_warehouse = status == EquipmentStatus.in_stock
    
    # If on warehouse, clear location
    if item.is_warehouse:
        item.location = None
    else:
        item.location = location.strip() or None
    
    await db.commit()
    return RedirectResponse(url=f"/equipment/{item.id}", status_code=303)


@router.post("/{equipment_id}/delete")
async def equipment_delete(
    equipment_id: int,
    user: User = Depends(require_role(UserRole.engineer, UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Equipment).filter(Equipment.id == equipment_id))
    item = result.scalar_one_or_none()
    if item:
        await db.delete(item)
        await db.commit()
    return RedirectResponse(url="/equipment", status_code=303)
