"""
Notification Dispatcher — routing event ke channel yang tepat.
"""
import structlog
from core.config import get_settings
from core.constants import NotifType, NotifChannel

log = structlog.get_logger(__name__)
settings = get_settings()


class NotificationDispatcher:
    def __init__(self):
        self._telegram = None
        self._email = None

    async def start(self):
        if settings.TELEGRAM_BOT_TOKEN:
            from services.notifier.telegram import TelegramNotifier
            self._telegram = TelegramNotifier()
        log.info("notifier.started")

    async def stop(self):
        pass

    async def send_motion_alert(self, camera_id: str, zone: str, frame, severity: int):
        log.info("notifier.motion", camera=camera_id, zone=zone, severity=severity)
        if self._telegram:
            await self._telegram.send_motion(camera_id, zone, frame, severity)

    async def send_camera_offline(self, camera_id: str):
        log.warning("notifier.camera_offline", camera=camera_id)
        if self._telegram:
            await self._telegram.send_text(f"🔴 Kamera OFFLINE: {camera_id}")

    async def send_disk_alert(self, drive: str, free_pct: float):
        log.warning("notifier.disk_alert", drive=drive, free_pct=free_pct)
        if self._telegram:
            await self._telegram.send_text(
                f"⚠️ Storage rendah!\nDrive: {drive}\nSisa: {free_pct:.1f}%"
            )
