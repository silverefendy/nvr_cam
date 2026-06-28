"""
MotionManager — manage all MotionDetector instances.
"""
import asyncio
from backend.core.logging import get_logger
from backend.services.motion.detector import MotionDetector
from backend.services.notifier.telegram import notify_motion

logger = get_logger(__name__, service="motion")


class MotionManager:
    def __init__(self):
        self.detectors: dict[str, MotionDetector] = {}
        self._running = False

    async def start_all(self, cameras: list[dict]):
        """Start motion detection for all motion-enabled cameras."""
        self._running = True
        motion_cameras = [c for c in cameras if c.get("motion_enabled")]
        logger.info(f"Starting motion detection for {len(motion_cameras)} cameras")
        
        tasks = []
        for cam in motion_cameras:
            detector = MotionDetector(cam, on_motion_callback=self._handle_motion)
            self.detectors[cam["id"]] = detector
            tasks.append(detector.run())
        
        await asyncio.gather(*tasks, return_exceptions=True)

    async def stop_all(self):
        """Stop all motion detectors."""
        self._running = False
        logger.info("Motion detection stopped")

    async def _handle_motion(self, camera_id: str, zone_name: str, snapshot_path: str):
        """Called when motion detected — save to DB and notify."""
        logger.info(f"Motion detected: {camera_id} zone={zone_name}")
        
        # Save to DB
        from backend.db.base import AsyncSessionLocal
        from backend.db.repositories.event_repo import EventRepository
        from backend.db.models.motion_event import MotionEvent
        from datetime import datetime, timezone
        
        try:
            async with AsyncSessionLocal() as db:
                event_repo = EventRepository(db)
                event = MotionEvent(
                    camera_id=camera_id,
                    zone_name=zone_name,
                    started_at=datetime.now(timezone.utc),
                    snapshot_path=snapshot_path,
                    severity=1,
                    notified=False
                )
                await event_repo.create(event)
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to save motion event to DB: {e}")
        
        # Send Telegram notification
        detector = self.detectors.get(camera_id)
        if detector:
            camera_name = detector.camera.get("name", camera_id)
            await notify_motion(camera_name, zone_name, snapshot_path)
