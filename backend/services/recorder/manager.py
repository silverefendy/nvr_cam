"""
RecordingManager — mengelola semua CameraRecorder sekaligus.
Singleton yang di-start saat aplikasi boot.
"""
import asyncio
from datetime import datetime, timezone
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
        "storage_drive": cam.storage_drive,
        "motion_enabled": cam.motion_enabled,
        "retention_days": cam.retention_days,
        "segment_duration": config_extra.get("segment_duration", 3600),
        "is_active": cam.is_active,
        "config_json": cam.config_json,
    }


class RecordingManager:
    """Singleton — satu instance untuk semua kamera."""
    _instance: "RecordingManager | None" = None

    def __init__(self):
        self.recorders: dict[str, CameraRecorder] = {}
        self._running = False
        self._reconnect_delay = 30

    @classmethod
    def get_instance(cls) -> "RecordingManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

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
        """Restart recording for a single camera (load fresh config from DB)."""
        # Stop recorder lama jika ada
        if camera_id in self.recorders:
            await self.recorders[camera_id].stop()
            del self.recorders[camera_id]

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
            else:
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
