import os
import uuid as uuid_mod
import json
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.config import settings
from app.database import get_db
from app.models.user import User, AccessRequest, Department, Division, ProfileChangeRequest
from app.models.chat import Chat, ChatMember
from app.auth_client import auth_client
from app.services.auth import get_current_user, security as auth_security
from app.services.profiles import resolve_users_map

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ===========================================================================
# ВХОД — только через портал (auth-service)
# ===========================================================================

@router.post("/login")
async def login_disabled():
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Вход выполняется через портал ДГИ. Перейдите на портал и откройте мессенджер из списка сервисов.",
    )


# ===========================================================================
# ЗАПРОС НА ДОСТУП (вместо регистрации)
# ===========================================================================

@router.post("/access-request")
async def create_access_request(data: dict, db: AsyncSession = Depends(get_db)):
    # Проверка что email не занят
    existing = await db.execute(select(User).where(User.email == data.get("email")))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Пользователь с таким email уже существует")

    existing_req = await db.execute(
        select(AccessRequest).where(
            AccessRequest.email == data.get("email"),
            AccessRequest.status == "pending"
        )
    )
    if existing_req.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Запрос с таким email уже отправлен и ожидает рассмотрения")

    dept_id = data.get("department_id") or None
    div_id = data.get("division_id") or None

    request = AccessRequest(
        first_name=data.get("first_name", ""),
        last_name=data.get("last_name", ""),
        patronymic=data.get("patronymic") or None,
        email=data.get("email", ""),
        phone=data.get("phone") or None,
        department_id=dept_id,
        division_id=div_id,
        position=data.get("position") or None,
        reason=data.get("reason") or None,
    )
    db.add(request)
    return {"message": "Запрос отправлен в Управление информатизации"}


@router.get("/departments")
async def get_departments(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Department).where(Department.is_active == True))
    departments = result.scalars().all()
    return [{"id": str(d.id), "name": d.name, "short_name": d.short_name} for d in departments]


@router.get("/divisions/{department_id}")
async def get_divisions(department_id: str, db: AsyncSession = Depends(get_db)):
    import uuid as uuid_mod
    result = await db.execute(
        select(Division).where(Division.department_id == uuid_mod.UUID(department_id), Division.is_active == True)
    )
    divisions = result.scalars().all()
    return [{"id": str(d.id), "name": d.name, "short_name": d.short_name} for d in divisions]


# ===========================================================================
# ПРОФИЛЬ
# ===========================================================================

@router.post("/refresh")
async def refresh_token_disabled():
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Обновление токена выполняется через портал / auth-service.",
    )


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    dept = None
    if current_user.department_id:
        r = await db.execute(select(Department).where(Department.id == current_user.department_id))
        dept = r.scalar_one_or_none()
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "patronymic": current_user.patronymic,
        "avatar_url": current_user.avatar_url,
        "phone": current_user.phone,
        "department": dept.name if dept else None,
        "department_id": str(current_user.department_id) if current_user.department_id else None,
        "position": current_user.position,
        "role": current_user.role,
        "status": current_user.status,
        "password_expired": current_user.password_expired,
        "avatar_visibility": current_user.avatar_visibility or "all",
        "avatar_visibility_list": json.loads(current_user.avatar_visibility_list) if current_user.avatar_visibility_list else [],
    }


@router.put("/me/avatar")
async def update_avatar(data: dict, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    current_user.avatar_url = data.get("avatar_url")
    db.add(current_user)
    return {"message": "Аватар обновлён", "avatar_url": current_user.avatar_url}


@router.post("/me/avatar/upload")
async def upload_avatar(file: UploadFile = File(...), current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    ext = os.path.splitext(file.filename or "avatar.png")[1] or ".png"
    save_name = f"avatar_{current_user.id}_{uuid_mod.uuid4().hex[:8]}{ext}"
    save_path = os.path.join(settings.UPLOAD_DIR, save_name)
    content = await file.read()
    with open(save_path, "wb") as f:
        f.write(content)
    url = f"/uploads/{save_name}"
    current_user.avatar_url = url
    db.add(current_user)
    return {"message": "Аватар обновлён", "avatar_url": url}


@router.delete("/me/avatar")
async def delete_avatar(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # Delete the file if it exists
    if current_user.avatar_url and current_user.avatar_url.startswith("/uploads/"):
        file_path = os.path.join(settings.UPLOAD_DIR, current_user.avatar_url.replace("/uploads/", ""))
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass  # Ignore file deletion errors
    current_user.avatar_url = None
    db.add(current_user)
    return {"message": "Аватар удалён"}


@router.put("/me/avatar-visibility")
async def update_avatar_visibility(data: dict, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    visibility = data.get("visibility", "all")
    if visibility not in ("all", "contacts", "selected", "except"):
        raise HTTPException(status_code=400, detail="Неверный тип видимости")
    current_user.avatar_visibility = visibility
    user_ids = data.get("user_ids", [])
    current_user.avatar_visibility_list = json.dumps(user_ids) if user_ids else None
    db.add(current_user)
    return {"message": "Настройки видимости обновлены"}


@router.put("/me/password")
async def change_password(
    data: dict,
    credentials: HTTPAuthorizationCredentials = Depends(auth_security),
):
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Смена пароля выполняется в единой учётной записи (портал / auth-service).",
    )


@router.post("/me/request-name-change")
async def request_name_change(data: dict, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    field = data.get("field")  # first_name, last_name, patronymic
    new_value = data.get("new_value", "").strip()
    if field not in ("first_name", "last_name", "patronymic"):
        raise HTTPException(status_code=400, detail="Недопустимое поле")
    if not new_value:
        raise HTTPException(status_code=400, detail="Значение не может быть пустым")

    old_value = getattr(current_user, field, "")
    request = ProfileChangeRequest(
        user_id=current_user.id,
        field_name=field,
        old_value=old_value,
        new_value=new_value,
    )
    db.add(request)
    return {"message": "Запрос на изменение отправлен в Управление информатизации"}


# ===========================================================================
# ПОИСК ПОЛЬЗОВАТЕЛЕЙ
# ===========================================================================

@router.get("/users")
async def search_users(
    q: str = "",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(auth_security),
):
    if not q or len(q) < 2:
        query = select(User).where(User.is_active == True, User.id != current_user.id).limit(50)
        result = await db.execute(query)
        users = result.scalars().all()
    else:
        auth_hits = await auth_client.search_users(credentials.credentials, q)
        ids = [uuid_mod.UUID(u["id"]) for u in auth_hits if u.get("id")]
        users_map = await resolve_users_map(db, ids)
        users = [users_map[uid] for uid in ids if uid in users_map and uid != current_user.id]
    from app.routers.websocket import manager as ws_manager
    
    # Check if current user has chat with target user for "contacts" visibility
    async def has_chat_with(target_user_id):
        chat_result = await db.execute(
            select(ChatMember).where(
                and_(
                    ChatMember.user_id == current_user.id,
                    ChatMember.chat_id.in_(
                        select(ChatMember.chat_id).where(ChatMember.user_id == target_user_id)
                    )
                )
            )
        )
        return chat_result.scalar_one_or_none() is not None
    
    async def get_avatar_url(user):
        if not user.avatar_url:
            return None
        visibility = user.avatar_visibility or "all"
        if visibility == "all":
            return user.avatar_url
        elif visibility == "contacts":
            return user.avatar_url if await has_chat_with(user.id) else None
        elif visibility == "selected":
            if not user.avatar_visibility_list:
                return None
            allowed_ids = json.loads(user.avatar_visibility_list)
            return user.avatar_url if str(current_user.id) in allowed_ids else None
        elif visibility == "except":
            if not user.avatar_visibility_list:
                return user.avatar_url
            excluded_ids = json.loads(user.avatar_visibility_list)
            return user.avatar_url if str(current_user.id) not in excluded_ids else None
        return user.avatar_url
    
    users_data = []
    for u in users:
        users_data.append({
            "id": str(u.id),
            "email": u.email,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "patronymic": u.patronymic,
            "avatar_url": await get_avatar_url(u),
            "position": u.position,
            "role": u.role,
            "department_id": str(u.department_id) if u.department_id else None,
            "status": "online" if ws_manager.is_online(str(u.id)) else (u.status or "offline"),
            "last_seen": u.last_seen.isoformat() if u.last_seen else None,
        })
    
    return users_data


@router.get("/users/{user_id}")
async def get_user(user_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    import uuid as uuid_mod
    try:
        uid = uuid_mod.UUID(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Некорректный user_id")
    res = await db.execute(select(User).where(User.id == uid))
    u = res.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    # Apply avatar visibility logic
    avatar_url = u.avatar_url
    if avatar_url:
        visibility = u.avatar_visibility or "all"
        if visibility == "all":
            avatar_url = u.avatar_url
        elif visibility == "contacts":
            # Check if they have a chat
            chat_result = await db.execute(
                select(ChatMember).where(
                    and_(
                        ChatMember.user_id == current_user.id,
                        ChatMember.chat_id.in_(
                            select(ChatMember.chat_id).where(ChatMember.user_id == u.id)
                        )
                    )
                )
            )
            avatar_url = u.avatar_url if chat_result.scalar_one_or_none() else None
        elif visibility == "selected":
            if u.avatar_visibility_list:
                allowed_ids = json.loads(u.avatar_visibility_list)
                avatar_url = u.avatar_url if str(current_user.id) in allowed_ids else None
            else:
                avatar_url = None
        elif visibility == "except":
            if u.avatar_visibility_list:
                excluded_ids = json.loads(u.avatar_visibility_list)
                avatar_url = u.avatar_url if str(current_user.id) not in excluded_ids else None
            else:
                avatar_url = u.avatar_url
    
    return {
        "id": str(u.id),
        "email": u.email,
        "first_name": u.first_name,
        "last_name": u.last_name,
        "patronymic": u.patronymic,
        "avatar_url": avatar_url,
        "position": u.position,
        "role": u.role,
    }


@router.get("/users/{user_id}/presence")
async def user_presence(user_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    import uuid as uuid_mod
    from app.routers.websocket import manager as ws_manager
    try:
        uid = uuid_mod.UUID(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Некорректный user_id")
    res = await db.execute(select(User).where(User.id == uid))
    u = res.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    online = ws_manager.is_online(str(u.id))
    return {
        "user_id": str(u.id),
        "status": "online" if online else (u.status or "offline"),
        "last_seen": u.last_seen.isoformat() if u.last_seen else None,
    }
