import uuid
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth_client import auth_client
from app.models.chat import Chat, ChatMember
from app.models.user import User


def _split_full_name(full_name: Optional[str], username: str) -> tuple[str, str, Optional[str]]:
    if not full_name:
        return username, "", None
    parts = full_name.strip().split()
    if len(parts) == 1:
        return parts[0], "", None
    if len(parts) == 2:
        return parts[0], parts[1], None
    return parts[0], parts[1], " ".join(parts[2:])


def _map_messenger_role(service_role: Optional[str], global_role: str) -> str:
    # Service role takes priority
    if service_role == "super_admin":
        return "super_admin"
    if service_role == "admin":
        return "admin"
    if service_role == "moderator":
        return "head"
    if service_role == "user":
        return "user"
    # Fallback to global role only if no service role
    if global_role == "admin":
        return "super_admin"
    return "user"


NEWS_CHANNEL_ID = uuid.UUID("00000000-0000-0000-0000-000000000100")


async def _ensure_news_channel(db: AsyncSession) -> Chat:
    """Гарантирует существование новостного канала «Новости ДГИ»."""
    news_result = await db.execute(select(Chat).where(Chat.is_news_channel == True).limit(1))
    news_channel = news_result.scalar_one_or_none()
    if news_channel is None:
        news_channel = Chat(
            id=NEWS_CHANNEL_ID,
            chat_type="channel",
            name="Новости ДГИ",
            description="Официальный новостной канал Департамента городского имущества",
            is_news_channel=True,
        )
        db.add(news_channel)
        await db.flush()
    return news_channel


async def _ensure_default_chats(db: AsyncSession, user_id: uuid.UUID, user_role: str = "user") -> None:
    # «Избранное» — личный чат сохранённых сообщений
    # Проверяем: есть ли у пользователя чат типа "saved" где он владелец
    saved_result = await db.execute(
        select(Chat)
        .join(ChatMember)
        .where(Chat.chat_type == "saved", Chat.owner_id == user_id)
        .limit(1)
    )
    if saved_result.scalar_one_or_none() is None:
        saved = Chat(chat_type="saved", name="Избранное", owner_id=user_id)
        db.add(saved)
        await db.flush()
        db.add(ChatMember(chat_id=saved.id, user_id=user_id, role="owner"))

    # Новостной канал «Новости ДГИ» — есть у всех, выйти нельзя
    news_channel = await _ensure_news_channel(db)
    member_result = await db.execute(
        select(ChatMember).where(
            ChatMember.chat_id == news_channel.id,
            ChatMember.user_id == user_id,
        )
    )
    existing_member = member_result.scalar_one_or_none()
    if existing_member is None:
        # Суперадмин получает роль admin для управления каналом
        role = "admin" if user_role == "super_admin" else "readonly"
        db.add(ChatMember(chat_id=news_channel.id, user_id=user_id, role=role))
    elif existing_member.role == "readonly" and user_role == "super_admin":
        # Обновляем роль если пользователь стал суперадмином
        existing_member.role = "admin"


async def ensure_messenger_profile(db: AsyncSession, auth_user: Dict[str, Any]) -> User:
    user_id = uuid.UUID(auth_user["id"])
    result = await db.execute(select(User).where(User.id == user_id))
    profile = result.scalar_one_or_none()

    first_name, last_name, patronymic = _split_full_name(
        auth_user.get("full_name"),
        auth_user.get("username") or auth_user.get("email") or "user",
    )
    service_access = await auth_client.get_messenger_access(str(user_id))
    service_role = service_access.get("role") if service_access else None
    role = _map_messenger_role(service_role, auth_user.get("role") or "user")

    if profile is None:
        profile = User(
            id=user_id,
            email=auth_user.get("email") or f"{auth_user.get('username')}@local",
            first_name=first_name,
            last_name=last_name,
            patronymic=patronymic,
            role=role,
            is_active=bool(auth_user.get("is_active", True)),
        )
        db.add(profile)
        await db.flush()
    else:
        profile.email = auth_user.get("email") or profile.email
        profile.first_name = first_name or profile.first_name
        profile.last_name = last_name or profile.last_name
        profile.patronymic = patronymic or profile.patronymic
        profile.role = role
        profile.is_active = bool(auth_user.get("is_active", True))
        db.add(profile)

    # Гарантируем наличие «Избранного» и новостного канала у ВСЕХ пользователей
    await _ensure_default_chats(db, user_id, role)

    await db.flush()
    return profile


async def resolve_users_map(
    db: AsyncSession,
    user_ids: Iterable[uuid.UUID],
) -> Dict[uuid.UUID, User]:
    ids = list({uid for uid in user_ids if uid})
    if not ids:
        return {}

    result = await db.execute(select(User).where(User.id.in_(ids)))
    found = {user.id: user for user in result.scalars().all()}
    missing = [str(uid) for uid in ids if uid not in found]
    if missing:
        contacts = await auth_client.get_contacts(missing)
        for contact in contacts:
            uid = uuid.UUID(contact["id"])
            first_name, last_name, patronymic = _split_full_name(
                contact.get("full_name"),
                contact.get("username") or contact.get("email") or "user",
            )
            profile = User(
                id=uid,
                email=contact.get("email") or f"{contact.get('username')}@local",
                first_name=first_name,
                last_name=last_name,
                patronymic=patronymic,
                role="user",
                is_active=True,
            )
            db.add(profile)
            found[uid] = profile
        await db.flush()

    return found
