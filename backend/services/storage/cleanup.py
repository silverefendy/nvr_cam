"""
Orphan Metadata Cleanup Worker — cleans up recordings and motion events with missing files.
"""
import asyncio
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.core.logging import get_logger
from backend.db.base import AsyncSessionLocal
from backend.db.models.recording import Recording
from backend.db.models.motion_event import MotionEvent

logger = get_logger(__name__, service="storage-cleanup")

async def cleanup_orphan_metadata(db: AsyncSession):
    """
    Scans the database for recordings and motion events referencing physical files
    that no longer exist on disk, and deletes those rows.
    """
    logger.info("[CLEANUP] Starting orphan metadata cleanup...")

    # 1. Clean up recordings
    try:
        result = await db.execute(select(Recording))
        recordings = result.scalars().all()
        deleted_recs = 0

        for rec in recordings:
            if not rec.file_path:
                continue
            path = Path(rec.file_path)
            if not path.exists():
                logger.info(f"[CLEANUP] Deleting orphan recording row ID={rec.id}, path={rec.file_path}")
                await db.delete(rec)
                deleted_recs += 1

        if deleted_recs > 0:
            await db.commit()
            logger.info(f"[CLEANUP] Successfully deleted {deleted_recs} orphan recording metadata rows")
    except Exception as e:
        logger.error(f"[CLEANUP] Error cleaning up orphan recordings: {e}")
        await db.rollback()

    # 2. Clean up motion events
    try:
        result = await db.execute(select(MotionEvent))
        events = result.scalars().all()
        deleted_events = 0

        for event in events:
            if not event.snapshot_path:
                continue
            path = Path(event.snapshot_path)
            if not path.exists():
                logger.info(f"[CLEANUP] Deleting orphan motion event row ID={event.id}, snapshot={event.snapshot_path}")
                await db.delete(event)
                deleted_events += 1

        if deleted_events > 0:
            await db.commit()
            logger.info(f"[CLEANUP] Successfully deleted {deleted_events} orphan motion event metadata rows")
    except Exception as e:
        logger.error(f"[CLEANUP] Error cleaning up orphan motion events: {e}")
        await db.rollback()

    logger.info("[CLEANUP] Orphan metadata cleanup finished.")


async def _cleanup_loop():
    """Background loop that runs the cleanup on startup and then every 6 hours."""
    # Delay slightly on startup to let DB/services initialize fully
    await asyncio.sleep(10)
    while True:
        try:
            async with AsyncSessionLocal() as db:
                await cleanup_orphan_metadata(db)
        except Exception as e:
            logger.error(f"[CLEANUP] Error in cleanup loop execution: {e}")

        # Wait 6 hours
        logger.info("[CLEANUP] Sleeping for 6 hours until next cleanup execution")
        await asyncio.sleep(6 * 3600)


def start_cleanup_worker():
    """Starts the background worker task."""
    asyncio.create_task(_cleanup_loop())
