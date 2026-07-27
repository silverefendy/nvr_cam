"""
RecordingManager — mengelola semua CameraRecorder sekaligus.
Singleton yang di-start saat aplikasi boot.
"""
import asyncio
from datetime import datetime, timezone
from collections import deque
from backend.core.logging import get_logger
from backend.db.base import AsyncSessionLocal
from backend.db.repositories.camera_repo import CameraRepository
from .camera_recorder import CameraRecorder

logger = get_logger(__name__, service="recorder")


def _camera_to_dict(cam) -> dict:
    """
    Konversi objek Camera (SQLAlchemy model) ke dict untuk CameraRecorder.
    segment_duration tidak ada sebagai kolom DB — diambil dari config_json
    dengan default 3600 (1 jam per segment).
    """
    config_extra = cam.config_json or {}
    return {
        "id": cam.id,
        "name": cam.name,
        "location": cam.location,
        "rtsp_main": cam.rtsp_main,
        "rtsp_sub": cam.rtsp_sub,
        "rtsp_url_main": cam.rtsp_url_main,
        "rtsp_url_sub": cam.rtsp_url_sub,
        "storage_drive": cam.storage_drive,
        "motion_enabled": cam.motion_enabled,
        "retention_days": cam.retention_days,
        "segment_duration": config_extra.get("segment_duration", 3600),
        "is_active": cam.is_active,
        "config_json": cam.config_json,
        "recording_schedule": cam.recording_schedule,
        "schedule_start_time": cam.schedule_start_time,
        "schedule_end_time": cam.schedule_end_time,
        "schedule_days": cam.schedule_days,
    }


class RecordingManager:
    """Singleton — satu instance untuk semua kamera."""
    _instance: "RecordingManager | None" = None

    def __init__(self):
        self.recorders: dict[str, CameraRecorder] = {}
        self._running = False
        self._reconnect_delay = 30
        # Per-camera lock: pastikan restart_camera tidak berjalan concurrent
        # untuk kamera yang sama (misal: user save 3x berturut-turut).
        self._restart_locks: dict[str, asyncio.Lock] = {}
        self.last_errors = deque(maxlen=10)

    @classmethod
    def get_instance(cls) -> "RecordingManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _get_restart_lock(self, camera_id: str) -> asyncio.Lock:
        """Ambil (atau buat) lock untuk camera_id tertentu."""
        if camera_id not in self._restart_locks:
            self._restart_locks[camera_id] = asyncio.Lock()
        return self._restart_locks[camera_id]

    async def load_cameras_from_db(self) -> list[dict]:
        """Load active cameras from database."""
        async with AsyncSessionLocal() as db:
            repo = CameraRepository(db)
            cameras = await repo.get_active_cameras()
            return [_camera_to_dict(cam) for cam in cameras]

    async def start_all(self, cameras: list[dict] = None):
        """Start recording semua kamera secara concurrent."""
        self._running = True

        if cameras is None:
            cameras = await self.load_cameras_from_db()

        logger.info(f"Memulai recording untuk {len(cameras)} kamera")
        tasks = []
        for cam in cameras:
            if cam.get("is_active", True):
                recorder = CameraRecorder(cam)
                self.recorders[cam["id"]] = recorder
                tasks.append(recorder.start())
        await asyncio.gather(*tasks, return_exceptions=True)

    async def stop_all(self):
        """Stop semua recorder dengan bersih."""
        self._running = False
        await asyncio.gather(*[r.stop() for r in self.recorders.values()])
        self.recorders.clear()

    async def restart_camera(self, camera_id: str):
        """
        Restart recording for a single camera (load fresh config from DB).

        Menggunakan per-camera asyncio.Lock agar tidak bisa dijalankan
        concurrent untuk kamera yang sama. Jika ada restart yang sedang
        berjalan, yang baru akan menunggu sampai selesai — sehingga
        konfigurasi terbaru yang selalu dipakai.

        Juga update storage_manager.camera_drive_map agar kamera baru
        langsung terdaftar untuk monitoring storage dan statistik.
        """
        lock = self._get_restart_lock(camera_id)
        async with lock:
            # Stop recorder lama jika ada
            if camera_id in self.recorders:
                await self.recorders[camera_id].stop()
                del self.recorders[camera_id]

            # Beri jeda singkat agar proses FFmpeg lama benar-benar mati
            # dan melepas file handle HLS sebelum recorder baru start.
            await asyncio.sleep(2)

            # Load config terbaru dari DB
            async with AsyncSessionLocal() as db:
                repo = CameraRepository(db)
                cam = await repo.get_by_id(camera_id)
                if cam and cam.is_active:
                    camera_dict = _camera_to_dict(cam)
                    recorder = CameraRecorder(camera_dict)
                    self.recorders[camera_id] = recorder
                    asyncio.create_task(recorder.start())
                    logger.info(f"Restarted recording for camera {camera_id}")

                    # Update storage_manager.camera_drive_map agar kamera baru
                    # terdaftar untuk monitoring storage dan cleanup otomatis.
                    # Import di dalam fungsi untuk hindari circular import.
                    try:
                        storage_manager = getattr(self, "storage_manager", None)
                        if storage_manager is not None:
                            storage_manager.update_camera_drive(camera_id, cam.storage_drive)
                            logger.info(f"[{camera_id}] Terdaftar di storage_manager: {cam.storage_drive}")
                    except Exception as e:
                        logger.warning(f"[{camera_id}] Gagal update storage_manager: {e}")

                else:
                    storage_manager = getattr(self, "storage_manager", None)
                    if storage_manager is not None:
                        storage_manager.remove_camera(camera_id)
                    logger.warning(f"Camera {camera_id} not found or inactive — recorder not started")

    def get_status(self, camera_id: str = None) -> dict | bool:
        """Return status for specific camera or all cameras."""
        if camera_id:
            recorder = self.recorders.get(camera_id)
            return recorder.is_alive if recorder else False
        return {cid: rec.is_alive for cid, rec in self.recorders.items()}

    def get_online_count(self) -> int:
        return sum(1 for alive in self.get_status().values() if alive)

    def get_offline_count(self) -> int:
        return len(self.recorders) - self.get_online_count()

    async def update_camera_status(self, camera_id: str, status: str):
        """Update camera status in database."""
        async with AsyncSessionLocal() as db:
            repo = CameraRepository(db)
            cam = await repo.get_by_id(camera_id)
            if cam:
                cam.status = status
                cam.last_seen = datetime.now(timezone.utc) if status == "online" else None
                await db.commit()

    def record_error(self, camera_id: str, error: str):
        self.last_errors.appendleft({
            "camera_id": camera_id,
            "error": error,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def get_recording_status(self) -> dict:
        status = {}
        for camera_id, recorder in self.recorders.items():
            status[camera_id] = {
                "is_recording": recorder.is_alive,
                "pid": recorder.recording_pid,
                "last_segment": (
                    recorder.segment_started_at.isoformat()
                    if recorder.segment_started_at else None
                ),
                "error": recorder.last_error,
            }
        return status
