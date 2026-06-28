"""
AV1 Encoder Scheduler — re-encode rekaman ke AV1 saat server idle.
Berjalan tiap malam jam 01:00-05:00.
"""
import asyncio
import yaml
from pathlib import Path
from datetime import datetime, time, timezone, timedelta
from backend.core.logging import get_logger
from backend.core.config import settings
from backend.services.recorder.ffmpeg_wrapper import build_av1_encode_command
from backend.db.base import AsyncSessionLocal
from backend.db.repositories.recording_repo import RecordingRepository
from backend.db.models.recording import Recording

logger = get_logger(__name__, service="encoder")


class EncoderScheduler:
    def __init__(self):
        self._running = False
        self._max_parallel = 3
        self._schedule_start = time(1, 0)  # 01:00
        self._schedule_stop = time(5, 0)   # 05:00
        self._av1_crf = 35
        self._av1_preset = 8

    async def start(self):
        """Start the encoder scheduler."""
        self._running = True
        logger.info("Encoder scheduler started")
        asyncio.create_task(self._scheduler_loop())

    def stop(self):
        """Stop the encoder scheduler."""
        self._running = False
        logger.info("Encoder scheduler stopped")

    async def _scheduler_loop(self):
        """Main scheduler loop."""
        while self._running:
            try:
                now = datetime.now(timezone.utc).time()
                
                # Check if we're within the encode window
                if self._schedule_start <= now < self._schedule_stop:
                    logger.info("Within encode window, starting encode job")
                    await self._run_encode_job()
                    # Sleep until next check (5 minutes)
                    await asyncio.sleep(300)
                else:
                    # Outside window, check every 5 minutes
                    await asyncio.sleep(300)
                    
            except Exception as e:
                logger.error(f"Error in encoder scheduler: {e}")
                await asyncio.sleep(60)

    async def _run_encode_job(self):
        """Run AV1 encoding for eligible recordings."""
        async with AsyncSessionLocal() as db:
            repo = RecordingRepository(db)
            
            # Get recordings that haven't been encoded to AV1
            # Filter: ended_at is not None, is_encoded_av1 is False
            # Only encode recordings from yesterday to avoid encoding recent files
            yesterday = datetime.now(timezone.utc) - timedelta(days=1)
            yesterday_start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
            yesterday_end = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            # Get recordings from yesterday that aren't encoded
            result = await db.execute(
                f"""
                SELECT * FROM recordings 
                WHERE ended_at IS NOT NULL 
                AND is_encoded_av1 = FALSE 
                AND started_at >= '{yesterday_start.isoformat()}'
                AND started_at <= '{yesterday_end.isoformat()}'
                ORDER BY started_at
                LIMIT {self._max_parallel}
                """
            )
            
            recordings = result.fetchall()
            
            if not recordings:
                logger.info("No recordings to encode")
                return
            
            logger.info(f"Encoding {len(recordings)} recordings to AV1")
            
            # Encode in parallel
            tasks = []
            for recording in recordings:
                tasks.append(self._encode_recording(recording))
            
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _encode_recording(self, recording: Recording):
        """Encode a single recording to AV1."""
        try:
            input_path = recording.file_path
            output_path = input_path.replace(".mp4", ".av1.mp4")
            
            # Check if input file exists
            if not Path(input_path).exists():
                logger.warning(f"Input file not found: {input_path}")
                return
            
            # Build FFmpeg command
            cmd = build_av1_encode_command(input_path, output_path, self._av1_crf)
            
            # Run FFmpeg
            import subprocess
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE
            )
            
            _, stderr = await process.communicate()
            
            if process.returncode == 0:
                # Success - update database
                async with AsyncSessionLocal() as db:
                    repo = RecordingRepository(db)
                    rec = await repo.get_by_id(recording.id)
                    if rec:
                        rec.is_encoded_av1 = True
                        # Optionally replace original with AV1 version
                        # For now, keep both
                        await db.commit()
                
                logger.info(f"Successfully encoded {input_path} to AV1")
            else:
                logger.error(f"Failed to encode {input_path}: {stderr.decode()}")
                
        except Exception as e:
            logger.error(f"Error encoding recording {recording.id}: {e}")
