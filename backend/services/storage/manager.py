"""
StorageManager — circular delete dan monitoring kapasitas disk.
Dijalankan sebagai background task tiap N menit.
"""
import shutil
import os
from pathlib import Path
from backend.core.logging import get_logger
from backend.core.config import settings

logger = get_logger(__name__, service="storage")


class StorageManager:
    def __init__(self, camera_drive_map: dict[str, str]):
        """
        camera_drive_map: {camera_id: drive_path}
        Contoh: {"cam_01": "/mnt/driveE", "cam_02": "/mnt/driveE"}
        """
        self.camera_drive_map = camera_drive_map
        self.threshold_pct = settings.storage_threshold_pct

    def get_drive_status(self, drive: str) -> dict:
        usage = shutil.disk_usage(drive)
        return {
            "path": drive,
            "total_gb": usage.total / (1024**3),
            "used_gb": usage.used / (1024**3),
            "free_gb": usage.free / (1024**3),
            "free_pct": (usage.free / usage.total) * 100,
        }

    def check_and_clean(self, drive: str, camera_id: str):
        """Hapus file terlama jika disk hampir penuh."""
        status = self.get_drive_status(drive)
        if status["free_pct"] >= self.threshold_pct:
            return  # masih aman

        logger.warning(f"Drive {drive} hampir penuh ({status['free_pct']:.1f}% sisa). Mulai cleanup.")
        cam_dir = Path(drive) / camera_id
        if not cam_dir.exists():
            return

        # Kumpulkan semua file .mp4 diurutkan dari terlama
        mp4_files = sorted(
            cam_dir.rglob("*.mp4"),
            key=lambda f: f.stat().st_mtime
        )

        for f in mp4_files:
            if status["free_pct"] >= self.threshold_pct + 5:
                break
            logger.info(f"Hapus file lama: {f}")
            f.unlink(missing_ok=True)
            # Hapus folder kosong
            try:
                f.parent.rmdir()
            except OSError:
                pass
            status = self.get_drive_status(drive)  # refresh

    def get_all_drives_status(self) -> list[dict]:
        drives = set(self.camera_drive_map.values())
        return [self.get_drive_status(d) for d in drives if Path(d).exists()]
