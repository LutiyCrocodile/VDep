"""Резервное копирование SQLite БД.

Используем родной механизм SQLite Online Backup API (sqlite3.Connection.backup).
Это безопасный hot-backup без блокировки приложения и без риска повреждения файла.
"""
import asyncio
import gzip
import hashlib
import logging
import os
import shutil
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List

from app.config import settings
from app.services.audit import audit

logger = logging.getLogger("backup")


def _sqlite_path_from_url(url: str) -> Optional[str]:
    """sqlite+aiosqlite:///./messenger.db  ->  ./messenger.db"""
    if "sqlite" not in url:
        return None
    if ":///" in url:
        return url.split(":///", 1)[1]
    return None


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _ensure_dir(p: str):
    Path(p).mkdir(parents=True, exist_ok=True)


def create_backup_sync(reason: str = "scheduled") -> Optional[dict]:
    """Синхронно создать сжатый бэкап БД. Возвращает метаданные или None."""
    db_path = _sqlite_path_from_url(settings.DATABASE_URL)
    if not db_path or not os.path.exists(db_path):
        logger.warning("backup: no SQLite DB file at %s", db_path)
        return None

    backup_dir = settings.BACKUP_DIR
    _ensure_dir(backup_dir)
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    raw_name = f"backup_{ts}_{reason}.db"
    raw_path = os.path.join(backup_dir, raw_name)

    # Hot-backup через sqlite3 backup API
    src = sqlite3.connect(db_path)
    dst = sqlite3.connect(raw_path)
    try:
        with dst:
            src.backup(dst)
    finally:
        src.close()
        dst.close()

    # Сжимаем
    gz_path = raw_path + ".gz"
    with open(raw_path, "rb") as f_in, gzip.open(gz_path, "wb", compresslevel=6) as f_out:
        shutil.copyfileobj(f_in, f_out)
    os.remove(raw_path)

    meta = {
        "file": os.path.basename(gz_path),
        "path": gz_path,
        "size": os.path.getsize(gz_path),
        "sha256": _sha256(gz_path),
        "reason": reason,
        "created_at": datetime.utcnow().isoformat(),
    }

    # Rotation: храним не более N
    _rotate_backups(backup_dir, settings.BACKUP_KEEP)
    return meta


def _rotate_backups(backup_dir: str, keep: int):
    files = sorted(
        [os.path.join(backup_dir, f) for f in os.listdir(backup_dir) if f.startswith("backup_") and f.endswith(".gz")],
        key=os.path.getmtime,
        reverse=True,
    )
    for old in files[keep:]:
        try:
            os.remove(old)
        except Exception:
            pass


def list_backups() -> List[dict]:
    backup_dir = settings.BACKUP_DIR
    if not os.path.isdir(backup_dir):
        return []
    out = []
    for fname in sorted(os.listdir(backup_dir), reverse=True):
        if fname.startswith("backup_") and fname.endswith(".gz"):
            full = os.path.join(backup_dir, fname)
            stat = os.stat(full)
            out.append({
                "file": fname,
                "size": stat.st_size,
                "created_at": datetime.utcfromtimestamp(stat.st_mtime).isoformat(),
            })
    return out


def check_db_integrity_sync() -> dict:
    """PRAGMA integrity_check + quick_check. Возвращает {'ok': bool, 'details': str}."""
    db_path = _sqlite_path_from_url(settings.DATABASE_URL)
    if not db_path or not os.path.exists(db_path):
        return {"ok": False, "details": "DB file not found"}
    con = sqlite3.connect(db_path)
    try:
        cur = con.cursor()
        cur.execute("PRAGMA integrity_check;")
        ic = cur.fetchone()
        cur.execute("PRAGMA quick_check;")
        qc = cur.fetchone()
        ok = (ic and ic[0] == "ok") and (qc and qc[0] == "ok")
        return {"ok": bool(ok), "details": f"integrity={ic[0] if ic else 'n/a'} quick={qc[0] if qc else 'n/a'}"}
    finally:
        con.close()


async def backup_worker():
    """Фоновая задача: периодические бэкапы + проверка целостности."""
    interval_seconds = max(60, settings.BACKUP_INTERVAL_HOURS * 3600)
    # Стартовый бэкап через минуту после запуска
    await asyncio.sleep(60)
    while True:
        try:
            # Сначала integrity check
            check = await asyncio.to_thread(check_db_integrity_sync)
            if not check["ok"]:
                # Аварийный бэкап и запись в аудит
                meta = await asyncio.to_thread(create_backup_sync, "integrity_fail")
                await audit(
                    "db_integrity_fail",
                    object_type="system",
                    status="failed",
                    details={"check": check, "emergency_backup": meta},
                )
                logger.error("DB integrity check failed: %s", check)
            else:
                meta = await asyncio.to_thread(create_backup_sync, "scheduled")
                if meta:
                    await audit(
                        "backup_create",
                        object_type="system",
                        object_id=meta["file"],
                        status="success",
                        details=meta,
                    )
                    logger.info("backup created: %s (%d bytes)", meta["file"], meta["size"])
        except Exception as e:
            logger.error("backup worker error: %s", e)
            await audit("backup_create", object_type="system", status="failed", details={"error": str(e)})
        await asyncio.sleep(interval_seconds)
