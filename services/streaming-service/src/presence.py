"""Счётчик одновременных зрителей эфира (in-memory, TTL по последнему heartbeat)."""
import time
from collections import defaultdict
from typing import Dict

_PRESENCE_TTL_SEC = 45
_presence: Dict[str, Dict[str, float]] = defaultdict(dict)


def touch_presence(stream_id: str, user_id: str) -> None:
    _presence[stream_id][user_id] = time.time()


def count_viewers(stream_id: str) -> int:
    now = time.time()
    users = _presence.get(stream_id, {})
    alive = {uid: ts for uid, ts in users.items() if now - ts < _PRESENCE_TTL_SEC}
    _presence[stream_id] = alive
    return len(alive)


def leave_presence(stream_id: str, user_id: str) -> None:
    users = _presence.get(stream_id)
    if users and user_id in users:
        del users[user_id]
