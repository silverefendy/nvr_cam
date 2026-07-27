"""
StorageManager — circular delete, monitoring kapasitas disk,
scheduled cleanup, dan alert Telegram saat disk kritis.
"""
import asyncio
import shutil
import os
from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy import select
from backend.core.logging import get_logger
from backend.core.config import settings
from backend.db.base import AsyncSessionLocal
from backend.db.models.recording import Recording
from backend.utils.config_manager import config_manager
from backend.services.storage.cleanup import cleanup_orphan_metadata

logger = get_logger(__name__, service="storage")

_ALERT_COOLDOWN_MINUTES = 60


class StorageManager:
    def __init__(self, camera_drive_map: dict[str, str]):
        """
        camera_drive_map: {camera_id: drive_path}
        Contoh: {"cam_01": "/mnt/driveE", "cam_02": "/mnt/driveE"}
        """
        self.camera_drive_map = camera_drive_map
        self.threshold_pct = settings.storage_threshold_pct
        self._running = False
        self._last_alert: dict[str, datetime] = {}
        self.dispatcher = None

    # ─────────────────────────────────────────────────────────────────────────
    # Status & statistik
    # ─────────────────────────────────────────────────────────────────────────

    def get_drive_status(self, drive: str) -> dict:
        usage = shutil.disk_usage(drive)
        return {
            "path": drive,
            "total_gb": usage.total / (1024 ** 3),
            "used_gb": usage.used / (1024 ** 3),
            "free_gb": usage.free / (1024 ** 3),
            "free_pct": (usage.free / usage.total) * 100,
        }

    def get_all_drives_status(self) -> list[dict]:
        drives = set(self.camera_drive_map.values())
        return [self.get_drive_status(d) for d in drives if Path(d).exists()]

    def update_camera_drive(self, camera_id: str, drive_path: str) -> None:
        self.camera_drive_map[camera_id] = drive_path
        logger.info(f"[STORAGE] camera_id={camera_id} mapped ke {drive_path}")

    def get_drive_for_camera(self, camera_id: str) -> str | None:
        drive = self.camera_drive_map.get(camera_id)
        if not drive:
            logger.warning(f"[STORAGE] camera_drive_map tidak ada entry untuk camera_id={camera_id}")
        return drive

    def remove_camera(self, camera_id: str) -> None:
        self.camera_drive_map.pop(camera_id, None)

    def get_stats_by_camera(self) -> list[dict]:
        """
        Statistik penggunaan disk per kamera (F-08).
        Hitung total ukuran file .mp4 di folder masing-masing kamera.
        Return list dict: {camera_id, drive, file_count, total_mb}
        """
        result = []
        for cam_id, drive in self.camera_drive_map.items():
            cam_dir = Path(drive) / cam_id
            if not cam_dir.exists():
                result.append({
                    "camera_id": cam_id,
                    "drive": drive,
                    "file_count": 0,
                    "total_mb": 0.0,
                })
                continue

            mp4_files = list(cam_dir.rglob("*.mp4"))
            total_bytes = sum(f.stat().st_size for f in mp4_files if f.is_file())
            result.append({
                "camera_id": cam_id,
                "drive": drive,
                "file_count": len(mp4_files),
                "total_mb": round(total_bytes / (1024 ** 2), 2),
            })

        # Urutkan dari yang paling besar
        result.sort(key=lambda x: x["total_mb"], reverse=True)
        return result

    # ─────────────────────────────────────────────────────────────────────────
    # Cleanup & Purge
    # ─────────────────────────────────────────────────────────────────────────

    def check_and_clean(self, drive: str, camera_id: str):
        """Hapus file terlama jika disk hampir penuh."""
        status = self.get_drive_status(drive)
        if status["free_pct"] >= self.threshold_pct:
            return  # masih aman

        logger.warning(f"Drive {drive} hampir penuh ({status['free_pct']:.1f}% sisa). Mulai cleanup.")
        cam_dir = Path(drive) / camera_id
        if not cam_dir.exists():
            return

        mp4_files = sorted(
            cam_dir.rglob("*.mp4"),
            key=lambda f: f.stat().st_mtime
        )

        for f in mp4_files:
            if status["free_pct"] >= self.threshold_pct + 5:
                break
            logger.info(f"Hapus file lama: {f}")
            f.unlink(missing_ok=True)
            try:
                f.parent.rmdir()
            except OSError:
                pass
            status = self.get_drive_status(drive)

    async def auto_purge_storage(self, db):
        """
        Enforce disk quotas automatically:
        If disk usage > 90% (or DB-configured threshold), delete oldest unprotected
        recordings and their files in batches until usage <= 80% (or DB safe threshold).
        After each batch, trigger cleanup_orphan_metadata.
        """
        logger.info("[PURGE] Starting auto purge storage check...")

        # Load DB configs
        sys_config = await config_manager.get_system_config()
        storage_section = sys_config.get("storage", {})

        # We calculate limits. default threshold is 90% used (sisa free < 10%)
        # but threshold_pct is defined as free percentage or used percentage?
        # In .env: STORAGE_THRESHOLD_PCT=10.0 (free percentage, so <10% sisa disk triggers warning)
        # Task 2B says: "If usage > 90% (threshold configurable via DB settings table, default 90), delete oldest recordings... until usage <= 80%"
        # Usage > 90% is equivalent to sisa disk < 10%. Let's use usage percentage (used / total * 100) > threshold.
        # threshold from DB or default 90%. safe_threshold from DB or default 80%.
        purge_threshold = float(storage_section.get("threshold_pct", 90.0))
        safe_threshold = float(storage_section.get("safe_threshold_pct", 80.0))

        # Gather all distinct drive paths from cameras mapped in StorageManager
        drives = set(self.camera_drive_map.values())

        for drive in drives:
            p = Path(drive)
            if not p.exists():
                continue

            try:
                usage = shutil.disk_usage(drive)
                used_pct = (usage.used / usage.total) * 100
                logger.info(f"[PURGE] Drive {drive} usage: {used_pct:.1f}% (limit: {purge_threshold:.1f}%)")

                if used_pct <= purge_threshold:
                    continue

                logger.warning(f"[PURGE] Drive {drive} usage ({used_pct:.1f}%) exceeds threshold ({purge_threshold:.1f}%). Purging oldest recordings...")

                # Fetch all unprotected recordings sorted oldest first
                stmt = select(Recording).where(Recording.is_protected == False).order_by(Recording.started_at.asc())
                res = await db.execute(stmt)
                all_unprotected = res.scalars().all()

                # Filter recordings residing on this drive
                drive_recs = [r for r in all_unprotected if r.file_path and r.file_path.startswith(drive)]

                if not drive_recs:
                    logger.warning(f"[PURGE] No unprotected recordings found on drive {drive} to purge.")
                    continue

                # Delete in batches of 10
                batch_size = 10
                idx = 0
                while used_pct > safe_threshold and idx < len(drive_recs):
                    batch = drive_recs[idx : idx + batch_size]
                    idx += batch_size

                    for rec in batch:
                        # 1. Delete physical file
                        rec_file = Path(rec.file_path)
                        freed_bytes = 0
                        if rec_file.exists():
                            try:
                                freed_bytes = rec_file.stat().st_size
                                rec_file.unlink(missing_ok=True)
                            except Exception as e:
                                logger.error(f"[PURGE] Failed to delete file {rec.file_path}: {e}")

                        # 2. Delete database row
                        await db.delete(rec)
                        logger.info(f"[PURGE] Deleted camera_id={rec.camera_id}, path={rec.file_path}, freed {freed_bytes} bytes")

                    # Commit batch
                    await db.commit()

                    # 3. Call cleanup orphan metadata
                    await cleanup_orphan_metadata(db)

                    # Recalculate usage
                    usage = shutil.disk_usage(drive)
                    used_pct = (usage.used / usage.total) * 100
                    logger.info(f"[PURGE] Post-batch drive {drive} usage: {used_pct:.1f}% (safe: {safe_threshold:.1f}%)")

            except Exception as e:
                logger.error(f"[PURGE] Error purging drive {drive}: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # Alert Telegram (F-10)
    # ─────────────────────────────────────────────────────────────────────────

    async def _maybe_send_disk_alert(self, drive: str, free_pct: float):
        """
        Kirim alert Telegram saat disk kritis.
        Dilengkapi cooldown agar tidak spam saat kondisi belum berubah.
        """
        if self.dispatcher is None:
            return

        now = datetime.now(timezone.utc)
        last = self._last_alert.get(drive)

        if last is not None:
            elapsed_minutes = (now - last).total_seconds() / 60
            if elapsed_minutes < _ALERT_COOLDOWN_MINUTES:
                return

        self._last_alert[drive] = now
        try:
            await self.dispatcher.send_disk_alert(drive, free_pct)
            logger.info(f"Alert disk terkirim: {drive} ({free_pct:.1f}% sisa)")
        except Exception as e:
            logger.error(f"Gagal kirim alert disk: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # Background loop
    # ─────────────────────────────────────────────────────────────────────────

    async def monitor_loop(self):
        """
        Background loop untuk monitoring dan cleanup otomatis.
        - Cek disk setiap 15 menit
        - Jika disk kritis: auto-purge + cleanup + kirim alert Telegram (F-10)
        """
        self._running = True
        check_interval = 15 * 60  # 15 menit

        while self._running:
            try:
                # Run auto purge first using a DB session
                async with AsyncSessionLocal() as db:
                    await self.auto_purge_storage(db)

                drives = set(self.camera_drive_map.values())
                for drive in drives:
                    if not Path(drive).exists():
                        continue

                    status = self.get_drive_status(drive)

                    if status["free_pct"] < self.threshold_pct:
                        await self._maybe_send_disk_alert(drive, status["free_pct"])

                        cameras_on_drive = [
                            cam_id for cam_id, cam_drive in self.camera_drive_map.items()
                            if cam_drive == drive
                        ]
                        for cam_id in cameras_on_drive:
                            self.check_and_clean(drive, cam_id)

                await asyncio.sleep(check_interval)

            except Exception as e:
                logger.error(f"Error in storage monitor loop: {e}")
                await asyncio.sleep(60)
