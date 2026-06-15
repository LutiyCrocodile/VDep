from datetime import datetime
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.database import get_db
from app.models.user import User
from app.models.chat import ChatMember
from app.models.message import Message, Poll, PollOption, PollVote
from app.services.auth import get_current_user

router = APIRouter(prefix="/api/polls", tags=["polls"])


@router.post("/")
async def create_poll(data: dict, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    import uuid as uuid_mod
    # Создаем сообщение типа poll
    message = Message(
        chat_id=uuid_mod.UUID(data["chat_id"]),
        sender_id=current_user.id,
        content=data["question"],
        message_type="poll",
    )
    db.add(message)
    await db.flush()

    # Создаем опрос
    poll = Poll(
        message_id=message.id,
        question=data["question"],
        is_anonymous=data.get("is_anonymous", False),
        is_multiple_choice=data.get("is_multiple_choice", False),
        closes_at=data.get("closes_at"),
    )
    db.add(poll)
    await db.flush()

    # Создаем варианты
    opts_list = []
    for i, opt_text in enumerate(data.get("options", [])):
        option = PollOption(poll_id=poll.id, option_text=opt_text, sort_order=i)
        db.add(option)
        opts_list.append(option)

    await db.flush()

    return {
        "id": str(message.id),
        "chat_id": str(message.chat_id),
        "sender_id": str(current_user.id),
        "sender_name": f"{current_user.first_name} {current_user.last_name}",
        "sender_avatar": current_user.avatar_url,
        "content": data["question"],
        "message_type": "poll",
        "created_at": message.created_at.isoformat() if message.created_at else None,
        "is_edited": False,
        "is_deleted": False,
        "attachments": [],
        "reactions": [],
        "reply_to": None,
        "poll": {
            "id": str(poll.id),
            "question": poll.question,
            "is_anonymous": poll.is_anonymous,
            "is_multiple_choice": poll.is_multiple_choice,
            "closes_at": None,
            "options": [
                {"id": str(o.id), "text": o.option_text, "vote_count": 0, "voted_by_me": False, "voters": []}
                for o in opts_list
            ],
            "total_votes": 0,
        },
    }


@router.get("/{poll_id}")
async def get_poll(poll_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    import uuid as uuid_mod
    result = await db.execute(select(Poll).where(Poll.id == uuid_mod.UUID(poll_id)))
    poll = result.scalar_one_or_none()
    if not poll:
        raise HTTPException(status_code=404, detail="Опрос не найден")

    options_data = []
    for opt in poll.options:
        vote_count = len(opt.votes)
        voted_by_me = any(v.user_id == current_user.id for v in opt.votes)
        voters = []
        if not poll.is_anonymous:
            voters = [str(v.user_id) for v in opt.votes]
        options_data.append({
            "id": str(opt.id),
            "text": opt.option_text,
            "vote_count": vote_count,
            "voted_by_me": voted_by_me,
            "voters": voters,
        })

    total_votes = sum(o["vote_count"] for o in options_data)

    return {
        "id": str(poll.id),
        "question": poll.question,
        "is_anonymous": poll.is_anonymous,
        "is_multiple_choice": poll.is_multiple_choice,
        "closes_at": poll.closes_at.isoformat() if poll.closes_at else None,
        "options": options_data,
        "total_votes": total_votes,
    }


@router.post("/{poll_id}/vote")
async def vote(poll_id: str, data: dict, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    import uuid as uuid_mod
    result = await db.execute(select(Poll).where(Poll.id == uuid_mod.UUID(poll_id)))
    poll = result.scalar_one_or_none()
    if not poll:
        raise HTTPException(status_code=404, detail="Опрос не найден")

    if poll.closes_at and datetime.utcnow() > poll.closes_at:
        raise HTTPException(status_code=400, detail="Опрос завершён")

    option_ids = data.get("option_ids", [])
    if not option_ids:
        raise HTTPException(status_code=400, detail="Выберите вариант")

    if not poll.is_multiple_choice and len(option_ids) > 1:
        raise HTTPException(status_code=400, detail="Можно выбрать только один вариант")

    # Удалить предыдущие голоса
    existing = await db.execute(
        select(PollVote).where(PollVote.poll_id == poll.id, PollVote.user_id == current_user.id)
    )
    for v in existing.scalars().all():
        await db.delete(v)

    # Добавить новые голоса
    for opt_id in option_ids:
        vote = PollVote(
            poll_id=poll.id,
            option_id=uuid_mod.UUID(opt_id),
            user_id=current_user.id,
        )
        db.add(vote)

    return {"message": "Голос принят"}
