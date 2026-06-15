from datetime import datetime, timezone
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.models.call import Call, CallParticipant
from app.services.auth import get_current_user
from sqlalchemy.orm import selectinload

router = APIRouter(prefix="/api/calls", tags=["calls"])


def _as_aware(dt):
    """Normalize a datetime to timezone-aware UTC. Returns None if dt is None."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _calc_duration(started_at, ended_at):
    """Safely compute duration in seconds handling naive/aware datetimes."""
    s = _as_aware(started_at)
    e = _as_aware(ended_at)
    if not s or not e:
        return None
    return int((e - s).total_seconds())


def get_avatar_url(user, current_user):
    """Apply avatar visibility logic"""
    if not user or not user.avatar_url:
        return None
    visibility = user.avatar_visibility or "all"
    if visibility == "all":
        return user.avatar_url
    elif visibility == "selected":
        if user.avatar_visibility_list:
            allowed_ids = json.loads(user.avatar_visibility_list)
            return user.avatar_url if str(current_user.id) in allowed_ids else None
        else:
            return None
    elif visibility == "except":
        if user.avatar_visibility_list:
            excluded_ids = json.loads(user.avatar_visibility_list)
            return user.avatar_url if str(current_user.id) not in excluded_ids else None
        else:
            return user.avatar_url
    return user.avatar_url


@router.get("/")
async def get_calls(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(
        select(Call)
        .options(selectinload(Call.participants))
        .join(CallParticipant).where(
            CallParticipant.user_id == current_user.id
        ).order_by(Call.created_at.desc()).limit(50)
    )
    calls = result.scalars().all()
    items = []
    for c in calls:
        items.append({
            "id": str(c.id),
            "chat_id": str(c.chat_id) if c.chat_id else None,
            "initiator_id": str(c.initiator_id),
            "call_type": c.call_type,
            "status": c.status,
            "scheduled_at": c.scheduled_at.isoformat() if c.scheduled_at else None,
            "started_at": c.started_at.isoformat() if c.started_at else None,
            "ended_at": c.ended_at.isoformat() if c.ended_at else None,
            "duration": c.duration,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "participants": [{
                "user_id": str(p.user_id),
                "first_name": None,  # Removed relationship loading
                "last_name": None,
                "avatar_url": None,
                "is_muted": p.is_muted,
                "is_camera_off": p.is_camera_off,
                "is_screen_sharing": p.is_screen_sharing,
            } for p in c.participants]
        })
    return items


@router.post("/")
async def start_call(data: dict, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Check if user is frozen
    if current_user.is_frozen:
        raise HTTPException(status_code=403, detail="Ваш аккаунт заморожен. Звонки запрещены.")
    
    import uuid as uuid_mod
    from app.models.chat import Chat, ChatMember

    try:
        chat_uuid = uuid_mod.UUID(data["chat_id"]) if data.get("chat_id") else None

        # ── Проверка прав на звонок в каналах ──────────────────────────────
        if chat_uuid:
            ch_res = await db.execute(select(Chat).where(Chat.id == chat_uuid))
            chat = ch_res.scalar_one_or_none()
            if chat and (chat.chat_type == "channel" or chat.is_news_channel):
                # Только владелец/админ канала может начать трансляцию
                mem_res = await db.execute(
                    select(ChatMember).where(
                        ChatMember.chat_id == chat_uuid,
                        ChatMember.user_id == current_user.id,
                    )
                )
                mem = mem_res.scalar_one_or_none()
                if not mem or mem.role not in ("owner", "admin"):
                    raise HTTPException(
                        status_code=403,
                        detail="В каналах звонки запрещены. Только администратор канала может начать трансляцию.",
                    )

        # Для каналов трансляция начинается сразу (active), для обычных чатов - ringing
        is_broadcast = data.get("is_broadcast", False)
        initial_status = "active" if is_broadcast else "ringing"

        call = Call(
            chat_id=chat_uuid,
            initiator_id=current_user.id,
            call_type=data.get("call_type", "audio"),
            status=initial_status,
            started_at=datetime.utcnow() if is_broadcast else None,
        )
        db.add(call)
        await db.flush()

        # Добавить инициатора как участника
        db.add(CallParticipant(call_id=call.id, user_id=current_user.id, joined_at=datetime.utcnow() if is_broadcast else None))

        # Добавить остальных участников (для обычных звонков)
        if not is_broadcast:
            for uid in data.get("participant_ids", []):
                db.add(CallParticipant(call_id=call.id, user_id=uuid_mod.UUID(uid)))

        await db.commit()
        return {"id": str(call.id), "status": initial_status}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error starting call: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Ошибка при создании звонка")


@router.post("/schedule")
async def schedule_call(data: dict, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Check if user is frozen
    if current_user.is_frozen:
        raise HTTPException(status_code=403, detail="Ваш аккаунт заморожен. Звонки запрещены.")
    
    import uuid as uuid_mod
    from datetime import timedelta
    from dateutil.parser import parse
    from app.models.chat import Chat, ChatMember
    from app.models.message import Message
    from app.routers.websocket import manager

    scheduled_at = parse(data["scheduled_at"]) if isinstance(data.get("scheduled_at"), str) else data.get("scheduled_at")

    participant_ids = [uuid_mod.UUID(uid) for uid in data.get("participant_ids", [])]

    call = Call(
        chat_id=uuid_mod.UUID(data["chat_id"]) if data.get("chat_id") else None,
        initiator_id=current_user.id,
        call_type=data.get("call_type", "audio"),
        status="scheduled",
        scheduled_at=scheduled_at,
    )
    db.add(call)
    await db.flush()

    for pid in participant_ids:
        db.add(CallParticipant(call_id=call.id, user_id=pid))

    # ── Системное сообщение о запланированном звонке ───────────────────
    # Собираем имена участников (инициатор + приглашённые)
    all_user_ids = [current_user.id] + participant_ids
    users_res = await db.execute(select(User).where(User.id.in_(all_user_ids)))
    users = {u.id: u for u in users_res.scalars().all()}
    names = [f"{u.first_name} {u.last_name}".strip() for u in users.values()]

    # Время в локальном формате (UTC+3)
    local_time = scheduled_at + timedelta(hours=3)
    time_str = local_time.strftime("%d.%m.%Y в %H:%M")
    call_kind = "видеозвонок" if data.get("call_type") == "video" else "звонок"
    content = f"📅 Запланирован {call_kind} на {time_str}\nУчастники: {', '.join(names)}"

    async def _ensure_private_chat(other_id):
        # Найти существующий приватный чат между current_user и other_id
        existing = await db.execute(
            select(Chat).join(ChatMember).where(
                Chat.chat_type == "private",
                ChatMember.user_id == current_user.id,
            )
        )
        for ch in existing.scalars().all():
            mids = [m.user_id for m in ch.members]
            if other_id in mids and current_user.id in mids and len(mids) == 2:
                return ch
        # Создать новый приватный чат
        ch = Chat(chat_type="private", owner_id=current_user.id)
        db.add(ch)
        await db.flush()
        db.add(ChatMember(chat_id=ch.id, user_id=current_user.id, role="owner"))
        db.add(ChatMember(chat_id=ch.id, user_id=other_id, role="member"))
        return ch

    # Создаём системное сообщение в личном чате с каждым участником
    for pid in participant_ids:
        chat = await _ensure_private_chat(pid)
        msg = Message(
            chat_id=chat.id,
            sender_id=current_user.id,
            content=content,
            message_type="system",
        )
        db.add(msg)
        await db.flush()

        # Уведомляем участника по WebSocket (live-добавление сообщения)
        await manager.send_to_user(str(pid), {
            "type": "new_message",
            "chat_id": str(chat.id),
            "message": {
                "id": str(msg.id),
                "chat_id": str(chat.id),
                "sender_id": str(current_user.id),
                "content": content,
                "message_type": "system",
                "is_system": True,
                "created_at": msg.created_at.isoformat() if msg.created_at else datetime.utcnow().isoformat(),
            },
        })

    return {"id": str(call.id), "status": "scheduled", "scheduled_at": scheduled_at.isoformat()}


@router.post("/{call_id}/join")
async def join_call(call_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Check if user is frozen
    if current_user.is_frozen:
        raise HTTPException(status_code=403, detail="Ваш аккаунт заморожен. Звонки запрещены.")
    
    import uuid as uuid_mod
    from app.models.chat import Chat, ChatMember

    # Validate call_id before UUID conversion
    if not call_id or call_id == "undefined":
        raise HTTPException(status_code=400, detail="Invalid call_id")
    try:
        call_uuid = uuid_mod.UUID(call_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid call_id format")

    try:
        result = await db.execute(select(Call).where(Call.id == call_uuid))
        call = result.scalar_one_or_none()
        if not call:
            raise HTTPException(status_code=404, detail="Звонок не найден")

        # Проверить, что пользователь является членом чата (кроме трансляций в каналах)
        if call.chat_id:
            chat_result = await db.execute(select(Chat).where(Chat.id == call.chat_id))
            chat = chat_result.scalar_one_or_none()
            is_broadcast = chat and (chat.chat_type == "channel" or chat.is_news_channel)

            if not is_broadcast:
                mem_result = await db.execute(
                    select(ChatMember).where(
                        ChatMember.chat_id == call.chat_id,
                        ChatMember.user_id == current_user.id,
                    )
                )
                member = mem_result.scalar_one_or_none()
                if not member:
                    raise HTTPException(
                        status_code=403,
                        detail="Вы не являетесь участником этого чата",
                    )

        # Проверить/добавить участника
        p_result = await db.execute(
            select(CallParticipant).where(CallParticipant.call_id == call.id, CallParticipant.user_id == current_user.id)
        )
        participant = p_result.scalar_one_or_none()
        if participant:
            participant.joined_at = datetime.utcnow()
            participant.left_at = None
        else:
            db.add(CallParticipant(call_id=call.id, user_id=current_user.id, joined_at=datetime.utcnow()))

        if call.status == "ringing":
            call.status = "active"
            call.started_at = datetime.utcnow()

        await db.commit()
        return {"status": "joined"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error joining call: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Ошибка при присоединении к звонку")


@router.post("/{call_id}/leave")
async def leave_call(call_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    import uuid as uuid_mod
    from app.models.chat import Chat
    from app.routers.websocket import manager

    # Validate call_id before UUID conversion
    if not call_id or call_id == "undefined":
        raise HTTPException(status_code=400, detail="Invalid call_id")
    try:
        call_uuid = uuid_mod.UUID(call_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid call_id format")

    result = await db.execute(
        select(CallParticipant).where(CallParticipant.call_id == call_uuid, CallParticipant.user_id == current_user.id)
    )
    participant = result.scalar_one_or_none()
    if participant:
        participant.left_at = datetime.now(timezone.utc)

    # Если все покинули — завершить (кроме трансляций в каналах)
    call_result = await db.execute(select(Call).where(Call.id == call_uuid))
    call = call_result.scalar_one_or_none()
    if call:
        # Проверяем, является ли это трансляцией в канале
        is_broadcast = False
        if call.chat_id:
            chat_result = await db.execute(select(Chat).where(Chat.id == call.chat_id))
            chat = chat_result.scalar_one_or_none()
            if chat and (chat.chat_type == "channel" or chat.is_news_channel):
                is_broadcast = True

        # Для обычных звонков завершаем, когда все покинули
        # Для трансляций в каналах - только владелец может завершить через /end
        if not is_broadcast:
            active_result = await db.execute(
                select(CallParticipant).where(
                    CallParticipant.call_id == call.id,
                    CallParticipant.joined_at != None,
                    CallParticipant.left_at == None
                )
            )
            active = active_result.scalars().all()
            if len(active) == 0:
                call.status = "ended"
                call.ended_at = datetime.now(timezone.utc)
                call.duration = _calc_duration(call.started_at, call.ended_at)

                # Отправляем call_end всем участникам звонка
                await manager.broadcast({
                    "type": "call_end",
                    "call_id": str(call.id),
                })

    return {"status": "left"}


@router.post("/{call_id}/end")
async def end_call(call_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    import uuid as uuid_mod
    import traceback

    print(f"[end_call] Attempting to end call: {call_id} by user: {current_user.id}")

    # Validate call_id before UUID conversion
    if not call_id or call_id == "undefined":
        print(f"[end_call] Invalid call_id: {call_id}")
        raise HTTPException(status_code=400, detail="Invalid call_id")
    try:
        call_uuid = uuid_mod.UUID(call_id)
    except ValueError as e:
        print(f"[end_call] Invalid UUID format: {call_id}, error: {e}")
        raise HTTPException(status_code=400, detail="Invalid call_id format")

    try:
        result = await db.execute(select(Call).where(Call.id == call_uuid))
        call = result.scalar_one_or_none()
        if not call:
            print(f"[end_call] Call not found: {call_uuid}")
            raise HTTPException(status_code=404, detail="Звонок не найден")

        print(f"[end_call] Found call: {call.id}, current status: {call.status}, started_at: {call.started_at}")

        call.status = "ended"
        call.ended_at = datetime.now(timezone.utc)
        call.duration = _calc_duration(call.started_at, call.ended_at)
        print(f"[end_call] Calculated duration: {call.duration} seconds")

        await db.commit()
        print(f"[end_call] Successfully ended call: {call.id}")
        return {"status": "ended"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[end_call] Error ending call: {e}")
        print(f"[end_call] Traceback: {traceback.format_exc()}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Ошибка при завершении звонка")


@router.post("/{call_id}/toggle-mute")
async def toggle_mute(call_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Check if user is frozen
    if current_user.is_frozen:
        raise HTTPException(status_code=403, detail="Ваш аккаунт заморожен. Звонки запрещены.")
    
    import uuid as uuid_mod
    # Validate call_id before UUID conversion
    if not call_id or call_id == "undefined":
        raise HTTPException(status_code=400, detail="Invalid call_id")
    try:
        call_uuid = uuid_mod.UUID(call_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid call_id format")

    result = await db.execute(
        select(CallParticipant).where(CallParticipant.call_id == call_uuid, CallParticipant.user_id == current_user.id)
    )
    p = result.scalar_one_or_none()
    if p:
        p.is_muted = not p.is_muted
        return {"is_muted": p.is_muted}
    raise HTTPException(status_code=404, detail="Участник не найден")


@router.post("/{call_id}/toggle-camera")
async def toggle_camera(call_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Check if user is frozen
    if current_user.is_frozen:
        raise HTTPException(status_code=403, detail="Ваш аккаунт заморожен. Звонки запрещены.")
    
    import uuid as uuid_mod
    # Validate call_id before UUID conversion
    if not call_id or call_id == "undefined":
        raise HTTPException(status_code=400, detail="Invalid call_id")
    try:
        call_uuid = uuid_mod.UUID(call_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid call_id format")

    result = await db.execute(
        select(CallParticipant).where(CallParticipant.call_id == call_uuid, CallParticipant.user_id == current_user.id)
    )
    p = result.scalar_one_or_none()
    if p:
        p.is_camera_off = not p.is_camera_off
        return {"is_camera_off": p.is_camera_off}
    raise HTTPException(status_code=404, detail="Участник не найден")


@router.post("/{call_id}/toggle-screen")
async def toggle_screen(call_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Check if user is frozen
    if current_user.is_frozen:
        raise HTTPException(status_code=403, detail="Ваш аккаунт заморожен. Звонки запрещены.")
    
    import uuid as uuid_mod
    # Validate call_id before UUID conversion
    if not call_id or call_id == "undefined":
        raise HTTPException(status_code=400, detail="Invalid call_id")
    try:
        call_uuid = uuid_mod.UUID(call_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid call_id format")

    result = await db.execute(
        select(CallParticipant).where(CallParticipant.call_id == call_uuid, CallParticipant.user_id == current_user.id)
    )
    p = result.scalar_one_or_none()
    if p:
        p.is_screen_sharing = not p.is_screen_sharing
        return {"is_screen_sharing": p.is_screen_sharing}
    raise HTTPException(status_code=404, detail="Участник не найден")


@router.post("/{call_id}/add-participant")
async def add_participant(call_id: str, data: dict, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Check if user is frozen
    if current_user.is_frozen:
        raise HTTPException(status_code=403, detail="Ваш аккаунт заморожен. Звонки запрещены.")
    
    import uuid as uuid_mod
    # Validate call_id before UUID conversion
    if not call_id or call_id == "undefined":
        raise HTTPException(status_code=400, detail="Invalid call_id")
    try:
        call_uuid = uuid_mod.UUID(call_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid call_id format")

    user_id = uuid_mod.UUID(data["user_id"])
    existing = await db.execute(
        select(CallParticipant).where(CallParticipant.call_id == call_uuid, CallParticipant.user_id == user_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Участник уже в звонке")
    db.add(CallParticipant(call_id=call_uuid, user_id=user_id))
    return {"message": "Участник добавлен"}
