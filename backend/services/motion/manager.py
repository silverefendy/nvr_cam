"""
MotionManager — kelola semua MotionDetector.
"""
import asyncio
import structlog
from services.motion.detector import MotionDetector
from utils.config_loader import load_cameras

log = structlog.get_logger(__name__)


class MotionManager:
    def __init__(self, notifier=None):
        self.detectors: dict[str, MotionDetector] = {}
        self.notifier = notifier

    async def start(self):
        cameras = load_cameras()
        motion_cameras = [c for c in cameras if c.get("motion_detect") and c.get("is_active")]
        log.info("motion.starting", count=len(motion_cameras))

        for cam in motion_cameras:
            detector = MotionDetector(cam, on_motion_callback=self._handle_motion)
            self.detectors[cam["id"]] = detector
            await detector.start()

    async def stop(self):
        tasks = [d.stop() for d in self.detectors.values()]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _handle_motion(self, camera_id: str, zone: str, frame, severity: int):
        """Dipanggil setiap motion terdeteksi — simpan ke DB dan notif."""
        log.info("motion.detected", camera=camera_id, zone=zone, severity=severity)
        # TODO: simpan snapshot, tulis ke DB, kirim notifikasi
        if self.notifier:
            await self.notifier.send_motion_alert(camera_id, zone, frame, severity)
