"""
StorageManager — circular delete, monitoring kapasitas disk,
scheduled cleanup, dan alert Telegram saat disk kritis.
"""
import asyncio
import shutil
from pathlib import Path
from datetime import datetime, timezone
from backend.core.logging import get_logger
from backend.core.config import settings

logger = get_logger(__name__, service="storage")

# Jeda minimum antar alert Telegram per drive (menit)
# Supaya tidak spam saat disk terus kritis
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
        # Cooldown tracker: {drive_path: last_alert_datetime}
        self._last_alert: dict[str, datetime] = {}
        # Dispatcher disuntikkan dari luar setelah app startup
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
    # Cleanup
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
                # Masih dalam cooldown, jangan kirim lagi
                return

        # Catat waktu alert dan kirim
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
        - Jika disk kritis: cleanup + kirim alert Telegram (F-10)
        """
        self._running = True
        check_interval = 15 * 60  # 15 menit

        while self._running:
            try:
                drives = set(self.camera_drive_map.values())
                for drive in drives:
                    if not Path(drive).exists():
                        continue

                    status = self.get_drive_status(drive)

                    if status["free_pct"] < self.threshold_pct:
                        # Kirim alert Telegram (F-10) — ada cooldown internal
                        await self._maybe_send_disk_alert(drive, status["free_pct"])

                        # Cleanup kamera di drive ini
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
