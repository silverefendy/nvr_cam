"""
RecordingManager — mengelola semua CameraRecorder sekaligus.
Singleton yang di-start saat aplikasi boot.
"""
import asyncio
from backend.core.logging import get_logger
from .camera_recorder import CameraRecorder

logger = get_logger(__name__, service="recorder")


class RecordingManager:
    """Singleton — satu instance untuk semua kamera."""
    _instance: "RecordingManager | None" = None

    def __init__(self):
        self.recorders: dict[str, CameraRecorder] = {}
        self._running = False

    @classmethod
    def get_instance(cls) -> "RecordingManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def start_all(self, cameras: list[dict]):
        """Start recording semua kamera secara concurrent."""
        self._running = True
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

    def get_status(self) -> dict[str, bool]:
        """Return dict {camera_id: is_alive} untuk health check."""
        return {cid: rec.is_alive for cid, rec in self.recorders.items()}

    def get_online_count(self) -> int:
        return sum(1 for alive in self.get_status().values() if alive)
