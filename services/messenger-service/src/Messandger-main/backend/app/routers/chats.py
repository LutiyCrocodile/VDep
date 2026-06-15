import uuid as uuid_mod
import os
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.models.chat import Chat, ChatMember
from app.models.message import Message, MessageAttachment, Reaction
from app.services.auth import get_current_user

router = APIRouter(prefix="/api/chats", tags=["chats"])


@router.get("/")
async def get_chats(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(
        select(Chat).join(ChatMember).where(ChatMember.user_id == current_user.id).order_by(Chat.updated_at.desc())
    )
    chats = result.scalars().all()
    items = []
    for chat in chats:
        # Получить последнее сообщение
        msg_result = await db.execute(
            select(Message).where(Message.chat_id == chat.id, Message.is_deleted == False)
            .order_by(Message.created_at.desc()).limit(1)
        )
        last_msg = msg_result.scalar_one_or_none()

        # Непрочитанные
        my_member = next((m for m in chat.members if m.user_id == current_user.id), None)
        unread = 0
        if my_member and my_member.last_read_message_id:
            unread_result = await db.execute(
                select(Message).where(
                    Message.chat_id == chat.id,
                    Message.created_at > (
                        select(Message.created_at).where(Message.id == my_member.last_read_message_id).scalar_subquery()
                    ),
                    Message.sender_id != current_user.id,
                    Message.is_deleted == False
                )
            )
            unread = len(unread_result.scalars().all())

        members_data = []
        for m in chat.members:
            u_result = await db.execute(select(User).where(User.id == m.user_id))
            u = u_result.scalar_one_or_none()
            if u:
                # Apply avatar visibility logic
                avatar_url = u.avatar_url
                if avatar_url:
                    visibility = u.avatar_visibility or "all"
                    if visibility == "contacts":
                        # Always show in chat members (they have chat)
                        avatar_url = u.avatar_url
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
                
                members_data.append({
                    "user_id": str(u.id),
                    "first_name": u.first_name,
                    "last_name": u.last_name,
                    "avatar_url": avatar_url,
                    "status": u.status,
                    "role": m.role,
                })

        last_message_data = None
        if last_msg:
            sender_result = await db.execute(select(User).where(User.id == last_msg.sender_id))
            sender = sender_result.scalar_one_or_none()
            last_message_data = {
                "id": str(last_msg.id),
                "content": last_msg.content,
                "sender_name": f"{sender.first_name} {sender.last_name}" if sender else "",
                "created_at": last_msg.created_at.isoformat() if last_msg.created_at else None,
                "message_type": last_msg.message_type,
            }

        items.append({
            "id": str(chat.id),
            "chat_type": chat.chat_type,
            "name": chat.name,
            "description": chat.description,
            "avatar_url": chat.avatar_url,
            "is_news_channel": chat.is_news_channel,
            "is_frozen": chat.is_frozen,
            "show_deleted_label": chat.show_deleted_label,
            "members": members_data,
            "last_message": last_message_data,
            "unread_count": unread,
            "is_pinned": my_member.is_pinned if my_member else False,
        })

    return items


@router.get("/all")
async def get_all_chats(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get all chats (super_admin only)"""
    if current_user.role != "super_admin":
        raise HTTPException(status_code=403, detail="Только суперадмин может видеть все чаты")
    
    result = await db.execute(
        select(Chat).order_by(Chat.updated_at.desc())
    )
    chats = result.scalars().all()
    items = []
    for chat in chats:
        # Skip saved chats (personal to each user)
        if chat.chat_type == "saved":
            continue
        
        members_data = []
        for m in chat.members:
            u_result = await db.execute(select(User).where(User.id == m.user_id))
            u = u_result.scalar_one_or_none()
            if u:
                # Apply avatar visibility logic
                avatar_url = u.avatar_url
                if avatar_url:
                    visibility = u.avatar_visibility or "all"
                    if visibility == "all":
                        avatar_url = u.avatar_url
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
                
                members_data.append({
                    "user_id": str(u.id),
                    "first_name": u.first_name,
                    "last_name": u.last_name,
                    "avatar_url": avatar_url,
                    "role": m.role,
                })

        items.append({
            "id": str(chat.id),
            "chat_type": chat.chat_type,
            "name": chat.name,
            "description": chat.description,
            "avatar_url": chat.avatar_url,
            "is_news_channel": chat.is_news_channel,
            "is_frozen": chat.is_frozen,
            "owner_id": str(chat.owner_id) if chat.owner_id else None,
            "members_count": len(chat.members),
            "members": members_data,
            "created_at": chat.created_at.isoformat() if chat.created_at else None,
        })

    return items


@router.post("/")
async def create_chat(data: dict, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Check if user is frozen
    if current_user.is_frozen:
        raise HTTPException(status_code=403, detail="Ваш аккаунт заморожен. Создание чатов запрещено.")
    
    chat_type = data.get("chat_type", "private")
    name = data.get("name")
    member_ids = data.get("member_ids", [])

    # Для приватного чата проверяем существующий
    if chat_type == "private" and len(member_ids) == 1:
        other_id = uuid_mod.UUID(member_ids[0])
        existing = await db.execute(
            select(Chat).join(ChatMember).where(
                Chat.chat_type == "private",
                ChatMember.user_id == current_user.id
            )
        )
        for chat in existing.scalars().all():
            member_ids_in_chat = [m.user_id for m in chat.members]
            if other_id in member_ids_in_chat and current_user.id in member_ids_in_chat and len(member_ids_in_chat) == 2:
                return {"id": str(chat.id), "existing": True}

    chat = Chat(
        chat_type=chat_type,
        name=name,
        owner_id=current_user.id,
    )
    db.add(chat)
    await db.flush()

    # Добавить создателя
    db.add(ChatMember(chat_id=chat.id, user_id=current_user.id, role="owner"))

    # Добавить участников
    for uid in member_ids:
        uid_parsed = uuid_mod.UUID(uid)
        if uid_parsed != current_user.id:
            role = "member"
            if chat_type == "channel":
                role = "readonly"
            elif chat_type == "group":
                u_result = await db.execute(select(User).where(User.id == uid_parsed))
                u = u_result.scalar_one_or_none()
                if u and u.role in ("head", "deputy_head", "super_admin", "admin"):
                    role = "admin"
            db.add(ChatMember(chat_id=chat.id, user_id=uid_parsed, role=role))

    return {"id": str(chat.id), "existing": False}


@router.get("/{chat_id}/messages")
async def get_messages(chat_id: str, limit: int = 50, offset: int = 0, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    cid = uuid_mod.UUID(chat_id)
    # Проверить членство
    member_check = await db.execute(
        select(ChatMember).where(ChatMember.chat_id == cid, ChatMember.user_id == current_user.id)
    )
    if not member_check.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Вы не участник этого чата")

    result = await db.execute(
        select(Message).where(Message.chat_id == cid, Message.is_scheduled == False)
        .options(selectinload(Message.reply_to))
        .order_by(Message.created_at.desc()).limit(limit).offset(offset)
    )
    messages = list(reversed(result.scalars().all()))

    # Compute read status: a message is "read" if every other chat member has
    # last_read_message_id pointing to a message at or after this one.
    members_result = await db.execute(
        select(ChatMember).where(ChatMember.chat_id == cid, ChatMember.user_id != current_user.id)
    )
    other_members = members_result.scalars().all()
    # Build a set of message IDs already read by every other member
    if other_members and messages:
        # For each other member, find index of their last_read in this messages list
        msg_ids_in_order = [m.id for m in messages]
        msg_index = {mid: i for i, mid in enumerate(msg_ids_in_order)}
        # Smallest index across all other members (everyone has read up to here)
        min_idx = len(msg_ids_in_order)  # default: no one has read anything visible
        for m in other_members:
            if m.last_read_message_id and m.last_read_message_id in msg_index:
                min_idx = min(min_idx, msg_index[m.last_read_message_id])
            else:
                min_idx = -1
                break
        read_by_all = set(msg_ids_in_order[: min_idx + 1]) if min_idx >= 0 else set()
    else:
        read_by_all = set()

    items = []
    for msg in messages:
        sender_result = await db.execute(select(User).where(User.id == msg.sender_id))
        sender = sender_result.scalar_one_or_none()
        
        # Apply avatar visibility logic for sender
        sender_avatar = None
        if sender and sender.avatar_url:
            visibility = sender.avatar_visibility or "all"
            if visibility == "all":
                sender_avatar = sender.avatar_url
            elif visibility == "contacts":
                # In chat context, always show (they have chat)
                sender_avatar = sender.avatar_url
            elif visibility == "selected":
                if sender.avatar_visibility_list:
                    allowed_ids = json.loads(sender.avatar_visibility_list)
                    sender_avatar = sender.avatar_url if str(current_user.id) in allowed_ids else None
                else:
                    sender_avatar = None
            elif visibility == "except":
                if sender.avatar_visibility_list:
                    excluded_ids = json.loads(sender.avatar_visibility_list)
                    sender_avatar = sender.avatar_url if str(current_user.id) not in excluded_ids else None
                else:
                    sender_avatar = sender.avatar_url

        reply_data = None
        if msg.reply_to:
            reply_sender_result = await db.execute(select(User).where(User.id == msg.reply_to.sender_id))
            reply_sender = reply_sender_result.scalar_one_or_none()
            reply_data = {
                "id": str(msg.reply_to.id),
                "content": msg.reply_to.content,
                "sender_name": f"{reply_sender.first_name} {reply_sender.last_name}" if reply_sender else "",
            }

        attachments_data = [{
            "id": str(a.id),
            "file_name": a.file_name,
            "file_url": a.file_url,
            "file_size": a.file_size,
            "file_type": a.file_type,
            "thumbnail_url": a.thumbnail_url,
        } for a in msg.attachments]

        reactions_data = [{
            "id": str(r.id),
            "emoji": r.emoji,
            "user_id": str(r.user_id),
        } for r in msg.reactions]

        poll_data = None
        if msg.message_type == "poll" and msg.poll:
            poll = msg.poll
            opts = []
            for opt in poll.options:
                opts.append({
                    "id": str(opt.id),
                    "text": opt.option_text,
                    "vote_count": len(opt.votes),
                    "voted_by_me": any(v.user_id == current_user.id for v in opt.votes),
                    "voters": [] if poll.is_anonymous else [str(v.user_id) for v in opt.votes],
                })
            poll_data = {
                "id": str(poll.id),
                "question": poll.question,
                "is_anonymous": poll.is_anonymous,
                "is_multiple_choice": poll.is_multiple_choice,
                "closes_at": poll.closes_at.isoformat() if poll.closes_at else None,
                "options": opts,
                "total_votes": sum(o["vote_count"] for o in opts),
            }

        items.append({
            "id": str(msg.id),
            "chat_id": str(msg.chat_id),
            "sender_id": str(msg.sender_id),
            "sender_name": f"{sender.first_name} {sender.last_name}" if sender else "",
            "sender_avatar": sender_avatar,
            "content": msg.content,
            "message_type": msg.message_type,
            "reply_to": reply_data,
            "is_edited": msg.is_edited,
            "is_deleted": msg.is_deleted,
            "is_pinned": msg.is_pinned,
            "allow_download": bool(getattr(msg, "allow_download", True)),
            "forwarded_from_id": str(msg.forwarded_from_id) if msg.forwarded_from_id else None,
            "attachments": attachments_data,
            "reactions": reactions_data,
            "poll": poll_data,
            "is_read": msg.id in read_by_all,
            "created_at": msg.created_at.isoformat() if msg.created_at else None,
        })

    return items


@router.post("/{chat_id}/messages")
async def send_message(chat_id: str, data: dict, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    cid = uuid_mod.UUID(chat_id)
    
    # Check if user is frozen
    if current_user.is_frozen:
        raise HTTPException(status_code=403, detail="Ваш аккаунт заморожен. Отправка сообщений запрещена.")
    
    # Check if chat is frozen
    chat_result = await db.execute(select(Chat).where(Chat.id == cid))
    chat = chat_result.scalar_one_or_none()
    if chat and chat.is_frozen:
        raise HTTPException(status_code=403, detail="Чат заморожен. Отправка сообщений запрещена.")
    
    member_check = await db.execute(
        select(ChatMember).where(ChatMember.chat_id == cid, ChatMember.user_id == current_user.id)
    )
    member = member_check.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=403, detail="Вы не участник этого чата")
    if member.role == "readonly":
        raise HTTPException(status_code=403, detail="У вас нет прав на отправку сообщений в этот канал")

    message = Message(
        chat_id=cid,
        sender_id=current_user.id,
        content=data.get("content"),
        message_type=data.get("message_type", "text"),
        reply_to_id=uuid_mod.UUID(data["reply_to_id"]) if data.get("reply_to_id") else None,
        allow_download=bool(data.get("allow_download", True)),
        scheduled_at=data.get("scheduled_at"),
        is_scheduled=bool(data.get("scheduled_at")),
    )
    db.add(message)
    await db.flush()

    # Load reply_to relationship for the response using separate query
    reply_data = None
    if message.reply_to_id:
        reply_result = await db.execute(
            select(Message).where(Message.id == message.reply_to_id)
        )
        reply_msg = reply_result.scalar_one_or_none()
        if reply_msg:
            reply_sender_result = await db.execute(select(User).where(User.id == reply_msg.sender_id))
            reply_sender = reply_sender_result.scalar_one_or_none()
            reply_data = {
                "id": str(reply_msg.id),
                "content": reply_msg.content,
                "sender_name": f"{reply_sender.first_name} {reply_sender.last_name}" if reply_sender else "",
            }

    # Apply avatar visibility logic for current user
    avatar_url = current_user.avatar_url
    if avatar_url:
        visibility = current_user.avatar_visibility or "all"
        if visibility == "all":
            avatar_url = current_user.avatar_url
        elif visibility == "selected":
            if current_user.avatar_visibility_list:
                # For own avatar, always show
                avatar_url = current_user.avatar_url
            else:
                avatar_url = None
        elif visibility == "except":
            if current_user.avatar_visibility_list:
                # For own avatar, always show
                avatar_url = current_user.avatar_url
            else:
                avatar_url = current_user.avatar_url

    # Обновить last_read
    member.last_read_message_id = message.id

    # Обновить chat.updated_at
    chat_result = await db.execute(select(Chat).where(Chat.id == cid))
    chat = chat_result.scalar_one_or_none()
    if chat:
        chat.updated_at = datetime.utcnow()

    # Load reply_to data if message is a reply
    reply_data = None
    if message.reply_to:
        reply_sender_result = await db.execute(select(User).where(User.id == message.reply_to.sender_id))
        reply_sender = reply_sender_result.scalar_one_or_none()
        reply_data = {
            "id": str(message.reply_to.id),
            "content": message.reply_to.content,
            "sender_name": f"{reply_sender.first_name} {reply_sender.last_name}" if reply_sender else "",
        }

    return {
        "id": str(message.id),
        "chat_id": str(message.chat_id),
        "sender_id": str(message.sender_id),
        "sender_name": f"{current_user.first_name} {current_user.last_name}",
        "sender_avatar": avatar_url,
        "content": message.content,
        "message_type": message.message_type,
        "allow_download": bool(message.allow_download),
        "forwarded_from_id": None,
        "created_at": message.created_at.isoformat() if message.created_at else None,
        "is_edited": False,
        "is_deleted": False,
        "attachments": [],
        "reactions": [],
        "reply_to": reply_data,
    }


@router.put("/{chat_id}/messages/{message_id}")
async def edit_message(chat_id: str, message_id: str, data: dict, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(
        select(Message).where(Message.id == uuid_mod.UUID(message_id), Message.sender_id == current_user.id)
    )
    message = result.scalar_one_or_none()
    if not message:
        raise HTTPException(status_code=404, detail="Сообщение не найдено")
    message.content = data.get("content", message.content)
    message.is_edited = True
    return {"message": "Обновлено"}


@router.delete("/{chat_id}/messages/{message_id}")
async def delete_message(chat_id: str, message_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    cid = uuid_mod.UUID(chat_id)
    result = await db.execute(
        select(Message).where(Message.id == uuid_mod.UUID(message_id), Message.sender_id == current_user.id)
    )
    message = result.scalar_one_or_none()
    if not message:
        # Проверяем: может админ чата или системный админ удалять чужое сообщение
        member_result = await db.execute(
            select(ChatMember).where(ChatMember.chat_id == cid, ChatMember.user_id == current_user.id)
        )
        member = member_result.scalar_one_or_none()
        is_chat_admin = member and member.role in ("owner", "admin")
        is_system_admin = current_user.role in ("head", "deputy_head", "super_admin")
        if not is_chat_admin and not is_system_admin:
            raise HTTPException(status_code=404, detail="Сообщение не найдено")
        result2 = await db.execute(select(Message).where(Message.id == uuid_mod.UUID(message_id)))
        message = result2.scalar_one_or_none()
        if not message:
            raise HTTPException(status_code=404, detail="Сообщение не найдено")

    # Определяем тип удаления
    chat_result = await db.execute(select(Chat).where(Chat.id == cid))
    chat = chat_result.scalar_one_or_none()

    # В каналах и избранном — всегда hard delete
    hard_delete = False
    if chat and (chat.chat_type in ("channel", "saved") or chat.is_news_channel):
        hard_delete = True
    elif chat and not chat.show_deleted_label:
        hard_delete = True

    if hard_delete:
        await db.delete(message)
    else:
        message.is_deleted = True
        message.content = None

    return {"message": "Удалено", "hard_delete": hard_delete}


@router.post("/{chat_id}/read")
async def mark_read(chat_id: str, data: dict, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    cid = uuid_mod.UUID(chat_id)
    result = await db.execute(
        select(ChatMember).where(ChatMember.chat_id == cid, ChatMember.user_id == current_user.id)
    )
    member = result.scalar_one_or_none()
    if member and data.get("message_id"):
        member.last_read_message_id = uuid_mod.UUID(data["message_id"])
    return {"ok": True}


@router.post("/{chat_id}/upload")
async def upload_file(
    chat_id: str,
    file: UploadFile = File(...),
    allow_download: bool = Form(True),
    content: str = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check if user is frozen
    if current_user.is_frozen:
        raise HTTPException(status_code=403, detail="Ваш аккаунт заморожен. Отправка сообщений запрещена.")
    
    cid = uuid_mod.UUID(chat_id)
    member_check = await db.execute(
        select(ChatMember).where(ChatMember.chat_id == cid, ChatMember.user_id == current_user.id)
    )
    member = member_check.scalar_one_or_none()
    if not member or member.role == "readonly":
        raise HTTPException(status_code=403, detail="Нет прав")

    # ---- Валидация: расширение и размер ----
    ext = os.path.splitext(file.filename or "")[1].lower().lstrip(".")
    if ext and ext not in settings.allowed_extensions:
        raise HTTPException(status_code=400, detail=f"Тип файла .{ext} не разрешён")

    # Сохранить файл (потоково, с контролем размера)
    file_id = str(uuid_mod.uuid4())
    save_name = f"{file_id}.{ext}" if ext else file_id
    save_path = os.path.join(settings.UPLOAD_DIR, save_name)
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    total = 0
    with open(save_path, "wb") as f:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                f.close()
                try:
                    os.remove(save_path)
                except Exception:
                    pass
                raise HTTPException(status_code=413, detail=f"Файл превышает {settings.MAX_UPLOAD_MB} МБ")
            f.write(chunk)

    file_url = f"/uploads/{save_name}"
    file_size = total
    file_type = file.content_type or "application/octet-stream"

    # Определить тип сообщения
    msg_type = "file"
    fname = file.filename or save_name
    if file_type.startswith("image"):
        msg_type = "image"
    elif file_type.startswith("video"):
        msg_type = "video"
    elif file_type.startswith("audio"):
        msg_type = "voice" if fname.startswith("voice_") else "audio"

    # Контент: если передан текст - используем его, иначе для медиа не показываем имя файла
    display_content = content if content and content.strip() else (None if msg_type in ("image", "video", "voice", "audio") else fname)

    # Создать сообщение с вложением
    message = Message(
        chat_id=cid,
        sender_id=current_user.id,
        content=display_content,
        message_type=msg_type,
        allow_download=bool(allow_download),
    )
    db.add(message)
    await db.flush()

    attachment = MessageAttachment(
        message_id=message.id,
        file_name=file.filename or save_name,
        file_url=file_url,
        file_size=file_size,
        file_type=file_type,
    )
    db.add(attachment)
    await db.flush()

    member.last_read_message_id = message.id
    chat_result = await db.execute(select(Chat).where(Chat.id == cid))
    chat_obj = chat_result.scalar_one_or_none()
    if chat_obj:
        chat_obj.updated_at = datetime.utcnow()

    return {
        "id": str(message.id),
        "chat_id": str(message.chat_id),
        "sender_id": str(message.sender_id),
        "sender_name": f"{current_user.first_name} {current_user.last_name}",
        "sender_avatar": current_user.avatar_url,
        "content": display_content,
        "message_type": msg_type,
        "allow_download": bool(message.allow_download),
        "forwarded_from_id": None,
        "created_at": message.created_at.isoformat() if message.created_at else None,
        "is_edited": False,
        "is_deleted": False,
        "attachments": [{
            "id": str(attachment.id),
            "file_name": attachment.file_name,
            "file_url": attachment.file_url,
            "file_size": attachment.file_size,
            "file_type": attachment.file_type,
            "thumbnail_url": None,
        }],
        "reactions": [],
        "reply_to": None,
    }


@router.post("/{chat_id}/members")
async def add_members(chat_id: str, data: dict, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Check if user is frozen
    if current_user.is_frozen:
        raise HTTPException(status_code=403, detail="Ваш аккаунт заморожен. Добавление участников запрещено.")
    
    cid = uuid_mod.UUID(chat_id)
    member_check = await db.execute(
        select(ChatMember).where(ChatMember.chat_id == cid, ChatMember.user_id == current_user.id)
    )
    member = member_check.scalar_one_or_none()
    if not member or member.role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Нет прав на добавление участников")

    chat_result = await db.execute(select(Chat).where(Chat.id == cid))
    chat_obj = chat_result.scalar_one_or_none()

    added = []
    for uid in data.get("user_ids", []):
        uid_parsed = uuid_mod.UUID(uid)
        existing = await db.execute(
            select(ChatMember).where(ChatMember.chat_id == cid, ChatMember.user_id == uid_parsed)
        )
        if existing.scalar_one_or_none():
            continue
        role = "member"
        if chat_obj:
            if chat_obj.chat_type == "channel" and not chat_obj.is_news_channel:
                role = "readonly"
            elif chat_obj.chat_type == "group":
                u_result = await db.execute(select(User).where(User.id == uid_parsed))
                u = u_result.scalar_one_or_none()
                if u and u.role in ("head", "deputy_head", "super_admin", "admin"):
                    role = "admin"
        db.add(ChatMember(chat_id=cid, user_id=uid_parsed, role=role))
        added.append(uid)

    return {"added": added, "count": len(added)}


@router.delete("/{chat_id}/members/{user_id}")
async def remove_member(chat_id: str, user_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    cid = uuid_mod.UUID(chat_id)
    member_check = await db.execute(
        select(ChatMember).where(ChatMember.chat_id == cid, ChatMember.user_id == current_user.id)
    )
    member = member_check.scalar_one_or_none()
    if not member or member.role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Нет прав")

    target = await db.execute(
        select(ChatMember).where(ChatMember.chat_id == cid, ChatMember.user_id == uuid_mod.UUID(user_id))
    )
    target_member = target.scalar_one_or_none()
    if target_member:
        await db.delete(target_member)
    return {"message": "Участник удалён"}


@router.post("/{chat_id}/leave")
async def leave_chat(chat_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    cid = uuid_mod.UUID(chat_id)
    
    # Check if chat exists
    chat_result = await db.execute(select(Chat).where(Chat.id == cid))
    chat = chat_result.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=404, detail="Чат не найден")
    
    # Restrict leaving "Новости ДГИ" channel
    if chat.is_news_channel and chat.name == "Новости ДГИ":
        raise HTTPException(status_code=403, detail="Нельзя выйти из канала «Новости ДГИ»")
    
    # Check if user is a member
    member_result = await db.execute(
        select(ChatMember).where(ChatMember.chat_id == cid, ChatMember.user_id == current_user.id)
    )
    member = member_result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Вы не участник этого чата")
    
    # Owner cannot leave (must transfer ownership or delete chat)
    if member.role == "owner":
        raise HTTPException(status_code=403, detail="Владелец не может выйти из чата")
    
    await db.delete(member)
    return {"message": "Вы вышли из чата"}


@router.delete("/{chat_id}")
async def delete_chat(chat_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    cid = uuid_mod.UUID(chat_id)
    
    # Check if chat exists
    chat_result = await db.execute(select(Chat).where(Chat.id == cid))
    chat = chat_result.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=404, detail="Чат не найден")
    
    # Restrict deleting "Новости ДГИ" channel
    if chat.is_news_channel and chat.name == "Новости ДГИ":
        raise HTTPException(status_code=403, detail="Нельзя удалить канал «Новости ДГИ»")
    
    # Super admin can delete any chat (except private chats and Новости ДГИ)
    if current_user.role == "super_admin":
        if chat.chat_type == "private":
            raise HTTPException(status_code=403, detail="Приватные чаты нельзя удалить")
    else:
        # Check if user is owner
        if chat.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="Только владелец может удалить чат")
        # Private chats cannot be deleted
        if chat.chat_type == "private":
            raise HTTPException(status_code=403, detail="Приватные чаты нельзя удалить")
    
    await db.delete(chat)
    return {"message": "Чат удалён"}


@router.post("/{chat_id}/freeze")
async def freeze_chat(chat_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Freeze or unfreeze a chat (super_admin only)"""
    if current_user.role != "super_admin":
        raise HTTPException(status_code=403, detail="Только суперадмин может замораживать чаты")
    
    cid = uuid_mod.UUID(chat_id)
    chat_result = await db.execute(select(Chat).where(Chat.id == cid))
    chat = chat_result.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=404, detail="Чат не найден")
    
    # Cannot freeze private chats or Новости ДГИ
    if chat.chat_type == "private":
        raise HTTPException(status_code=403, detail="Приватные чаты нельзя заморозить")
    if chat.is_news_channel and chat.name == "Новости ДГИ":
        raise HTTPException(status_code=403, detail="Нельзя заморозить канал «Новости ДГИ»")
    
    chat.is_frozen = not chat.is_frozen
    return {"message": "Чат заморожен" if chat.is_frozen else "Чат разморожен", "is_frozen": chat.is_frozen}


@router.put("/{chat_id}/settings")
async def update_chat_settings(chat_id: str, data: dict, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    cid = uuid_mod.UUID(chat_id)
    
    # Суперадмин может редактировать любой чат
    if current_user.role != 'super_admin':
        member_check = await db.execute(
            select(ChatMember).where(ChatMember.chat_id == cid, ChatMember.user_id == current_user.id)
        )
        member = member_check.scalar_one_or_none()
        if not member or member.role not in ("owner", "admin"):
            raise HTTPException(status_code=403, detail="Нет прав")

    chat_result = await db.execute(select(Chat).where(Chat.id == cid))
    chat = chat_result.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=404, detail="Чат не найден")

    if "name" in data:
        chat.name = data["name"]
    if "description" in data:
        chat.description = data["description"]
    if "show_deleted_label" in data:
        chat.show_deleted_label = data["show_deleted_label"]

    return {"message": "Настройки обновлены"}


@router.post("/{chat_id}/avatar/upload")
async def upload_chat_avatar(
    chat_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check if user is frozen
    if current_user.is_frozen:
        raise HTTPException(status_code=403, detail="Ваш аккаунт заморожен. Загрузка файлов запрещена.")
    
    try:
        cid = uuid_mod.UUID(chat_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Неверный ID чата")
    
    # Проверка прав
    if current_user.role != 'super_admin':
        member_check = await db.execute(
            select(ChatMember).where(ChatMember.chat_id == cid, ChatMember.user_id == current_user.id)
        )
        member = member_check.scalar_one_or_none()
        if not member or member.role not in ("owner", "admin"):
            raise HTTPException(status_code=403, detail="Нет прав")

    chat_result = await db.execute(select(Chat).where(Chat.id == cid))
    chat = chat_result.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=404, detail="Чат не найден")

    # Валидация файла
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Только изображения")

    # Сохранить файл
    file_id = str(uuid_mod.uuid4())
    ext = os.path.splitext(file.filename or "")[1].lower().lstrip(".") or "png"
    save_name = f"{file_id}.{ext}"
    save_path = os.path.join(settings.UPLOAD_DIR, save_name)
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    total = 0
    with open(save_path, "wb") as f:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                f.close()
                try:
                    os.remove(save_path)
                except Exception:
                    pass
                raise HTTPException(status_code=413, detail=f"Файл превышает {settings.MAX_UPLOAD_MB} МБ")
            f.write(chunk)

    # Удалить старый аватар
    if chat.avatar_url and chat.avatar_url.startswith("/uploads/"):
        try:
            old_path = os.path.join(settings.UPLOAD_DIR, chat.avatar_url.replace("/uploads/", ""))
            if os.path.exists(old_path):
                os.remove(old_path)
        except Exception:
            pass

    chat.avatar_url = f"/uploads/{save_name}"
    return {"avatar_url": chat.avatar_url}


@router.delete("/{chat_id}/avatar")
async def delete_chat_avatar(
    chat_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    cid = uuid_mod.UUID(chat_id)
    
    # Проверка прав
    if current_user.role != 'super_admin':
        member_check = await db.execute(
            select(ChatMember).where(ChatMember.chat_id == cid, ChatMember.user_id == current_user.id)
        )
        member = member_check.scalar_one_or_none()
        if not member or member.role not in ("owner", "admin"):
            raise HTTPException(status_code=403, detail="Нет прав")

    chat_result = await db.execute(select(Chat).where(Chat.id == cid))
    chat = chat_result.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=404, detail="Чат не найден")

    # Удалить файл
    if chat.avatar_url and chat.avatar_url.startswith("/uploads/"):
        try:
            old_path = os.path.join(settings.UPLOAD_DIR, chat.avatar_url.replace("/uploads/", ""))
            if os.path.exists(old_path):
                os.remove(old_path)
        except Exception:
            pass

    chat.avatar_url = None
    return {"message": "Аватар удален"}


@router.post("/{chat_id}/messages/{message_id}/reactions")
async def toggle_reaction(
    chat_id: str, message_id: str, data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check if user is frozen
    if current_user.is_frozen:
        raise HTTPException(status_code=403, detail="Ваш аккаунт заморожен. Отправка сообщений запрещена.")
    
    mid = uuid_mod.UUID(message_id)
    emoji = data.get("emoji", "")
    if not emoji:
        raise HTTPException(status_code=400, detail="Укажите эмодзи")

    existing = await db.execute(
        select(Reaction).where(
            Reaction.message_id == mid,
            Reaction.user_id == current_user.id,
            Reaction.emoji == emoji
        )
    )
    reaction = existing.scalar_one_or_none()
    if reaction:
        await db.delete(reaction)
        return {"action": "removed", "emoji": emoji}
    else:
        r = Reaction(message_id=mid, user_id=current_user.id, emoji=emoji)
        db.add(r)
        await db.flush()
        return {"action": "added", "emoji": emoji, "id": str(r.id)}


@router.get("/{chat_id}/messages/scheduled")
async def list_scheduled_messages(
    chat_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Return all scheduled (not yet sent) messages of the current user in this chat."""
    cid = uuid_mod.UUID(chat_id)
    result = await db.execute(
        select(Message).where(
            Message.chat_id == cid,
            Message.sender_id == current_user.id,
            Message.is_scheduled == True,
        ).order_by(Message.scheduled_at.asc())
    )
    items = []
    for msg in result.scalars().all():
        items.append({
            "id": str(msg.id),
            "content": msg.content,
            "message_type": msg.message_type,
            "scheduled_at": msg.scheduled_at.isoformat() if msg.scheduled_at else None,
            "created_at": msg.created_at.isoformat() if msg.created_at else None,
        })
    return items


@router.delete("/{chat_id}/messages/scheduled/{message_id}")
async def cancel_scheduled_message(
    chat_id: str, message_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Message).where(
            Message.id == uuid_mod.UUID(message_id),
            Message.sender_id == current_user.id,
            Message.is_scheduled == True,
        )
    )
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="Запланированное сообщение не найдено")
    await db.delete(msg)
    return {"ok": True}


@router.post("/{chat_id}/messages/schedule")
async def schedule_message(
    chat_id: str, data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check if user is frozen
    if current_user.is_frozen:
        raise HTTPException(status_code=403, detail="Ваш аккаунт заморожен. Отправка сообщений запрещена.")
    
    cid = uuid_mod.UUID(chat_id)
    member_check = await db.execute(
        select(ChatMember).where(ChatMember.chat_id == cid, ChatMember.user_id == current_user.id)
    )
    member = member_check.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=403, detail="Вы не участник этого чата")

    from dateutil.parser import parse
    scheduled_at = parse(data["scheduled_at"]) if isinstance(data.get("scheduled_at"), str) else data.get("scheduled_at")

    message = Message(
        chat_id=cid,
        sender_id=current_user.id,
        content=data.get("content"),
        message_type="text",
        scheduled_at=scheduled_at,
        is_scheduled=True,
    )
    db.add(message)
    await db.flush()

    return {
        "id": str(message.id),
        "chat_id": str(message.chat_id),
        "content": message.content,
        "scheduled_at": scheduled_at.isoformat() if scheduled_at else None,
        "is_scheduled": True,
    }


# ============================================================================
# Search messages
# ============================================================================
@router.get("/{chat_id}/messages/search")
async def search_messages(
    chat_id: str, q: str, limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cid = uuid_mod.UUID(chat_id)
    member_check = await db.execute(
        select(ChatMember).where(ChatMember.chat_id == cid, ChatMember.user_id == current_user.id)
    )
    if not member_check.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Вы не участник этого чата")

    if not q or not q.strip():
        return []
    pattern = f"%{q.strip()}%"
    result = await db.execute(
        select(Message).where(
            Message.chat_id == cid,
            Message.is_scheduled == False,
            Message.is_deleted == False,
            Message.content.ilike(pattern),
        ).order_by(Message.created_at.desc()).limit(limit)
    )
    msgs = result.scalars().all()
    items = []
    for m in msgs:
        sender_r = await db.execute(select(User).where(User.id == m.sender_id))
        sender = sender_r.scalar_one_or_none()
        items.append({
            "id": str(m.id),
            "chat_id": str(m.chat_id),
            "content": m.content,
            "sender_id": str(m.sender_id),
            "sender_name": f"{sender.first_name} {sender.last_name}" if sender else "",
            "created_at": m.created_at.isoformat() if m.created_at else None,
        })
    return items


# ============================================================================
# Media gallery for a chat (images / videos / files / audio / links)
# ============================================================================
@router.get("/{chat_id}/media")
async def chat_media(
    chat_id: str, kind: str = "image", limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """kind: image | video | file | audio | link"""
    cid = uuid_mod.UUID(chat_id)
    member_check = await db.execute(
        select(ChatMember).where(ChatMember.chat_id == cid, ChatMember.user_id == current_user.id)
    )
    if not member_check.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Вы не участник этого чата")

    if kind == "link":
        # Find messages containing URLs
        import re
        url_re = re.compile(r"https?://\S+")
        result = await db.execute(
            select(Message).where(
                Message.chat_id == cid,
                Message.is_scheduled == False,
                Message.is_deleted == False,
                Message.content.ilike("%http%"),
            ).order_by(Message.created_at.desc()).limit(limit)
        )
        out = []
        for m in result.scalars().all():
            for url in url_re.findall(m.content or ""):
                out.append({
                    "message_id": str(m.id),
                    "url": url,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                })
        return out

    # Map kind → message_type
    type_map = {
        "image": ["image"],
        "video": ["video"],
        "audio": ["audio", "voice"],
        "file": ["file"],
    }
    types = type_map.get(kind, ["file"])
    result = await db.execute(
        select(Message).where(
            Message.chat_id == cid,
            Message.is_scheduled == False,
            Message.is_deleted == False,
            Message.message_type.in_(types),
        ).order_by(Message.created_at.desc()).limit(limit)
    )
    items = []
    for m in result.scalars().all():
        for a in m.attachments:
            items.append({
                "message_id": str(m.id),
                "attachment_id": str(a.id),
                "file_name": a.file_name,
                "file_url": a.file_url,
                "file_size": a.file_size,
                "file_type": a.file_type,
                "allow_download": bool(getattr(m, "allow_download", True)),
                "created_at": m.created_at.isoformat() if m.created_at else None,
            })
    return items


# ============================================================================
# Forward a message to another chat
# ============================================================================
@router.post("/{chat_id}/messages/{message_id}/forward")
async def forward_message(
    chat_id: str, message_id: str, data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """data = { target_chat_ids: [str, ...] }"""
    # Check if user is frozen
    if current_user.is_frozen:
        raise HTTPException(status_code=403, detail="Ваш аккаунт заморожен. Отправка сообщений запрещена.")
    
    src_mid = uuid_mod.UUID(message_id)
    src_r = await db.execute(select(Message).where(Message.id == src_mid))
    src = src_r.scalar_one_or_none()
    if not src:
        raise HTTPException(status_code=404, detail="Сообщение не найдено")
    # Permission: must be a member of the source chat
    src_mem = await db.execute(
        select(ChatMember).where(ChatMember.chat_id == src.chat_id, ChatMember.user_id == current_user.id)
    )
    if not src_mem.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Нет доступа к исходному чату")

    targets = data.get("target_chat_ids") or []
    created = []
    for tgt in targets:
        try:
            tcid = uuid_mod.UUID(tgt)
        except Exception:
            continue
        # Must be member of target with write rights
        tgt_mem_r = await db.execute(
            select(ChatMember).where(ChatMember.chat_id == tcid, ChatMember.user_id == current_user.id)
        )
        tgt_mem = tgt_mem_r.scalar_one_or_none()
        if not tgt_mem or tgt_mem.role == "readonly":
            continue
        new_msg = Message(
            chat_id=tcid,
            sender_id=current_user.id,
            content=src.content,
            message_type=src.message_type,
            forwarded_from_id=src.id,
            allow_download=bool(getattr(src, "allow_download", True)),
        )
        db.add(new_msg)
        await db.flush()
        # Copy attachments
        for a in src.attachments:
            db.add(MessageAttachment(
                message_id=new_msg.id,
                file_name=a.file_name,
                file_url=a.file_url,
                file_size=a.file_size,
                file_type=a.file_type,
                thumbnail_url=a.thumbnail_url,
            ))
        tgt_mem.last_read_message_id = new_msg.id
        # bump chat
        chat_r = await db.execute(select(Chat).where(Chat.id == tcid))
        c = chat_r.scalar_one_or_none()
        if c:
            c.updated_at = datetime.utcnow()
        created.append(str(new_msg.id))
    return {"created": created, "count": len(created)}
