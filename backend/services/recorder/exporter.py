"""
Footage Exporter Service — merges and exports video clips from NVR recordings using FFmpeg concat.
"""
import asyncio
import os
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path
from sqlalchemy import select, and_
from backend.core.logging import get_logger
from backend.db.base import AsyncSessionLocal
from backend.db.models.recording import Recording
from backend.utils.config_manager import config_manager

logger = get_logger(__name__, service="exporter")


async def export_footage(db, camera_id: str, start_time: datetime, end_time: datetime) -> str:
    """
    Query recordings overlapping with range, generate concat list file, run FFmpeg to concat and trim,
    and save merged output to temp export directory.
    """
    logger.info(f"[EXPORT] Starting export for camera {camera_id} from {start_time} to {end_time}")

    # 1. Read temp export directory from DB settings (default /tmp/nvr_exports/)
    sys_config = await config_manager.get_system_config()
    export_dir_str = sys_config.get("general", {}).get("temp_export_dir", "/tmp/nvr_exports")
    export_dir = Path(export_dir_str)
    export_dir.mkdir(parents=True, exist_ok=True)

    # 2. Query recordings that overlap with [start_time, end_time]
    # Overlap condition: started_at < end_time AND (ended_at is None OR ended_at > start_time)
    stmt = select(Recording).where(
        and_(
            Recording.camera_id == camera_id,
            Recording.started_at < end_time,
            Recording.ended_at > start_time
        )
    ).order_by(Recording.started_at.asc())

    res = await db.execute(stmt)
    recordings = res.scalars().all()

    if not recordings:
        raise ValueError("Tidak ada rekaman video ditemukan dalam rentang waktu tersebut")

    # 3. Generate FFmpeg concat list file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    list_file_path = export_dir / f"concat_{camera_id}_{timestamp}.txt"
    output_file_path = export_dir / f"export_{camera_id}_{timestamp}.mp4"

    with open(list_file_path, "w", encoding="utf-8") as f:
        for rec in recordings:
            if not Path(rec.file_path).exists():
                logger.warning(f"[EXPORT] File path {rec.file_path} not found on disk, skipping.")
                continue

            f.write(f"file '{rec.file_path}'\n")

            # Trim the start of the first overlapping segment
            if rec.started_at < start_time:
                inpoint = (start_time - rec.started_at).total_seconds()
                f.write(f"inpoint {inpoint:.3f}\n")

            # Trim the end of the last overlapping segment
            if rec.ended_at and rec.ended_at > end_time:
                outpoint = (end_time - rec.started_at).total_seconds()
                f.write(f"outpoint {outpoint:.3f}\n")

    # 4. Run FFmpeg command: ffmpeg -f concat -safe 0 -i <list_file> -c copy <output.mp4>
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
        "-f", "concat", "-safe", "0", "-i", str(list_file_path),
        "-c", "copy", "-movflags", "+faststart", str(output_file_path)
    ]

    logger.info(f"[EXPORT] Running FFmpeg command: {' '.join(cmd)}")

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE
    )

    _, stderr = await process.communicate()

    # Clean up list file
    list_file_path.unlink(missing_ok=True)

    if process.returncode != 0:
        err_msg = stderr.decode(errors="replace").strip() if stderr else "Unknown FFmpeg error"
        logger.error(f"[EXPORT] FFmpeg failed with code {process.returncode}: {err_msg}")
        raise RuntimeError(f"FFmpeg gagal menggabungkan video: {err_msg}")

    logger.info(f"[EXPORT] Successfully exported footage to {output_file_path}")
    return str(output_file_path)


async def clean_old_exports():
    """Daily routine to delete export files older than 24 hours."""
    try:
        sys_config = await config_manager.get_system_config()
        export_dir_str = sys_config.get("general", {}).get("temp_export_dir", "/tmp/nvr_exports")
        export_dir = Path(export_dir_str)
        if not export_dir.exists():
            return

        now = datetime.now()
        deleted_count = 0
        for f in export_dir.glob("export_*_*.mp4"):
            stat = f.stat()
            age_hours = (now - datetime.fromtimestamp(stat.st_mtime)).total_seconds() / 3600.0
            if age_hours > 24.0:
                logger.info(f"[EXPORT] Cleaning up old export file {f.name} (age: {age_hours:.1f} hours)")
                f.unlink(missing_ok=True)
                deleted_count += 1

        if deleted_count > 0:
            logger.info(f"[EXPORT] Cleaned up {deleted_count} old export files")
    except Exception as e:
        logger.error(f"[EXPORT] Error cleaning up old exports: {e}")


async def _export_cleanup_loop():
    """Daily background task to run the cleanup."""
    while True:
        await clean_old_exports()
        # Wait 24 hours
        await asyncio.sleep(24 * 3600)


def start_export_cleanup_worker():
    """Starts the export cleanup background task."""
    asyncio.create_task(_export_cleanup_loop())
