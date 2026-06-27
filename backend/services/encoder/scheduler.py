"""
AV1 Encoder Scheduler — re-encode rekaman ke AV1 saat server idle.
Berjalan tiap malam jam 01:00-05:00.
"""
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import structlog

from core.config import get_settings
from services.encoder.av1_encoder import AV1Encoder

log = structlog.get_logger(__name__)
settings = get_settings()


class EncoderScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.encoder = AV1Encoder()

    def start(self):
        self.scheduler.add_job(
            self._run_encode,
            CronTrigger(hour=settings.AV1_ENCODE_HOUR, minute=0),
            id="av1_encode",
            replace_existing=True,
        )
        self.scheduler.start()
        log.info("encoder.scheduler.started", hour=settings.AV1_ENCODE_HOUR)

    def stop(self):
        self.scheduler.shutdown(wait=False)

    async def _run_encode(self):
        log.info("encoder.run.started")
        await self.encoder.encode_yesterday()
        log.info("encoder.run.finished")
