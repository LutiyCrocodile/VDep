"""Лёгкий in-memory счётчик метрик для /api/admin/metrics."""
from collections import defaultdict
from datetime import datetime
from threading import Lock

_lock = Lock()
_counters = defaultdict(int)
_started_at = datetime.utcnow()


def inc(name: str, value: int = 1):
    with _lock:
        _counters[name] += value


def snapshot() -> dict:
    with _lock:
        data = dict(_counters)
    data["uptime_seconds"] = int((datetime.utcnow() - _started_at).total_seconds())
    data["started_at"] = _started_at.isoformat()
    return data


def reset():
    with _lock:
        _counters.clear()
