"""Fan-out notifications to channel subscribers (new video, live stream)."""
from __future__ import annotations

import json
import logging
from typing import Optional

import httpx
import redis
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .database import Notification

logger = logging.getLogger(__name__)

_redis_client: Optional[redis.Redis] = None


def _redis() -> Optional[redis.Redis]:
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
            _redis_client.ping()
        except Exception as e:
            logger.warning("Redis unavailable for notification dedupe: %s", e)
            _redis_client = None
    return _redis_client


def _internal_headers() -> dict:
    return {"Authorization": f"Bearer {settings.internal_auth_token}"}


async def _fetch_subscriber_ids(channel_id: str) -> list[str]:
    url = f"{settings.video_service_url}/internal/channels/{channel_id}/subscriber-ids"
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(url, headers=_internal_headers())
        if r.status_code != 200:
            logger.error("subscriber-ids %s: %s", r.status_code, r.text)
            return []
        data = r.json()
        return [str(uid) for uid in data.get("subscriber_ids", [])]


async def _fetch_user_contact(user_id: str) -> Optional[dict]:
    url = f"{settings.auth_service_url}/internal/users/{user_id}/contact"
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(url, headers=_internal_headers())
        if r.status_code != 200:
            return None
        return r.json()


def _should_skip_stream_live(entity_id: str) -> bool:
    """True if this stream was already announced (duplicate RTMP hooks)."""
    key = f"notified:stream_live:{entity_id}"
    r = _redis()
    if r is None:
        return False
    try:
        return r.set(key, "1", nx=True, ex=86400) is None
    except Exception:
        return False


def _build_messages(
    event_type: str,
    channel_name: str,
    channel_handle: Optional[str],
    title: str,
    link_path: str,
) -> tuple[str, str, str]:
    channel_label = channel_name or channel_handle or "канал"
    if event_type == "new_video":
        in_app = f'На канале «{channel_label}» опубликовано новое видео: «{title}»'
        subject = f"Новое видео на канале {channel_label}"
        email_body = (
            f"<p>На канале <strong>{channel_label}</strong> опубликовано новое видео:</p>"
            f"<p><strong>{title}</strong></p>"
            f'<p><a href="{settings.frontend_public_url}{link_path}">Смотреть видео</a></p>'
        )
    else:
        in_app = f'Канал «{channel_label}» начал трансляцию: «{title}»'
        subject = f"Эфир на канале {channel_label}"
        email_body = (
            f"<p>Канал <strong>{channel_label}</strong> начал прямую трансляцию:</p>"
            f"<p><strong>{title}</strong></p>"
            f'<p><a href="{settings.frontend_public_url}{link_path}">Смотреть трансляцию</a></p>'
        )
    return in_app, subject, email_body


async def dispatch_channel_event(
    db: AsyncSession,
    *,
    event_type: str,
    channel_id: str,
    owner_id: str,
    channel_name: str,
    channel_handle: Optional[str],
    title: str,
    entity_id: str,
    link_path: str,
    push_ws,
    send_email_fn,
) -> int:
    """
    Notify all subscribers except the channel owner.
    Returns number of notifications created.
    """
    if event_type not in ("new_video", "stream_live"):
        return 0

    if event_type == "stream_live" and _should_skip_stream_live(entity_id):
        logger.info("stream_live already notified for %s", entity_id)
        return 0

    subscriber_ids = await _fetch_subscriber_ids(channel_id)
    owner_s = str(owner_id)
    recipients = [uid for uid in subscriber_ids if uid != owner_s]
    if not recipients:
        return 0

    in_app_msg, email_subject, email_html = _build_messages(
        event_type, channel_name, channel_handle, title, link_path
    )
    payload = {
        "event_type": event_type,
        "channel_id": channel_id,
        "channel_name": channel_name,
        "channel_handle": channel_handle,
        "entity_id": entity_id,
        "link_path": link_path,
        "title": title,
    }
    payload_json = json.dumps(payload, ensure_ascii=False)

    created = 0
    for user_id in recipients:
        notification = await Notification.create(
            db,
            user_id=user_id,
            type=event_type,
            message=in_app_msg,
            data=payload_json,
        )
        created += 1
        response = {
            "id": str(notification.id),
            "user_id": str(notification.user_id),
            "type": notification.type,
            "message": notification.message,
            "data": payload,
            "is_read": notification.is_read,
            "created_at": str(notification.created_at),
        }
        await push_ws(user_id, response)

        contact = await _fetch_user_contact(user_id)
        if contact and contact.get("email"):
            await send_email_fn(contact["email"], email_subject, email_html)

    logger.info(
        "channel event %s channel=%s notified %s subscribers",
        event_type,
        channel_id,
        created,
    )
    return created
