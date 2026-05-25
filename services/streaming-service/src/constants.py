"""Archive/RTMP constants."""
from __future__ import annotations

ARCHIVE_BLOCKING_PHASES = frozenset(
    {"pending", "waiting_recording", "uploading", "transcoding", "failed"}
)
ARCHIVE_IN_PROGRESS_PHASES = frozenset(
    {"pending", "waiting_recording", "uploading", "transcoding"}
)

RECORDING_SUFFIXES = (".mp4", ".m4v", ".webm", ".ts", ".m4s", ".part")


from typing import Dict, Set

_archive_tasks_inflight: Set[str] = set()
_rtmp_offline_streak: Dict[str, int] = {}
RTMP_OFFLINE_FINALIZE_AFTER = 3
