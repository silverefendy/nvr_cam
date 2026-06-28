"""
CameraRecorder — satu instance per kamera.
Mengelola FFmpeg process untuk recording dan HLS streaming.
"""
import asyncio
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from backend.core.logging import get_logger
from backend.core.exceptions import CameraConnectionError
from .ffmpeg_wrapper import build_record_command, build_hls_command

logger = get_logger(__name__, service="recorder")


class CameraRecorder:
    def __init__(self, camera: dict):
        self.camera = camera
        self.camera_id = camera["id"]
        self.record_process: subprocess.Popen | None = None
        self.hls_process: subprocess.Popen | None = None
        self.is_running = False
        self._reconnect_delay = 30  # detik
        self.current_file: str | None = None
        self.started_at: datetime | None = None
        self._last_seen: datetime | None = None

    async def start(self):
        """Start recording dan HLS streaming untuk kamera ini."""
        self.is_running = True
        self.started_at = datetime.now(timezone.utc)
        await asyncio.gather(
            self._run_recording_loop(),
            self._run_hls_loop(),
        )

    async def stop(self):
        """Stop semua proses FFmpeg dengan bersih."""
        self.is_running = False
        for proc in [self.record_process, self.hls_process]:
            if proc and proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()

    async def _run_recording_loop(self):
        """Loop recording dengan auto-reconnect jika FFmpeg mati."""
        from backend.services.recorder.manager import RecordingManager
        
        while self.is_running:
            try:
                output_dir = self._get_output_dir()
                output_dir.mkdir(parents=True, exist_ok=True)
                output_pattern = str(output_dir / "%H-%M-%S.mp4")

                cmd = build_record_command(self.camera["rtsp_main"], output_pattern)
                logger.info(f"[{self.camera_id}] Mulai recording")
                self.record_process = subprocess.Popen(
                    cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
                )
                
                # Update camera status to online
                manager = RecordingManager.get_instance()
                await manager.update_camera_status(self.camera_id, "online")
                self._last_seen = datetime.now(timezone.utc)
                
                # Tunggu sampai process mati
                await asyncio.get_event_loop().run_in_executor(
                    None, self.record_process.wait
                )
                
                if self.is_running:
                    logger.warning(f"[{self.camera_id}] FFmpeg mati, reconnect dalam {self._reconnect_delay}s")
                    await manager.update_camera_status(self.camera_id, "offline")
                    await asyncio.sleep(self._reconnect_delay)
            except Exception as e:
                logger.error(f"[{self.camera_id}] Error recording: {e}")
                if self.is_running:
                    await asyncio.sleep(self._reconnect_delay)

    async def _run_hls_loop(self):
        """Loop HLS streaming untuk live view browser."""
        hls_dir = f"/tmp/hls/{self.camera_id}"
        Path(hls_dir).mkdir(parents=True, exist_ok=True)
        while self.is_running:
            try:
                cmd = build_hls_command(
                    self.camera.get("rtsp_sub") or self.camera["rtsp_main"], hls_dir
                )
                self.hls_process = subprocess.Popen(
                    cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
                )
                await asyncio.get_event_loop().run_in_executor(
                    None, self.hls_process.wait
                )
                if self.is_running:
                    await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"[{self.camera_id}] Error HLS: {e}")
                await asyncio.sleep(10)

    def _get_output_dir(self) -> Path:
        drive = self.camera["storage_drive"]
        date_str = datetime.now().strftime("%Y-%m-%d")
        return Path(drive) / self.camera_id / date_str

    @property
    def is_alive(self) -> bool:
        return self.record_process is not None and self.record_process.poll() is None

    @property
    def last_seen(self) -> datetime | None:
        return self._last_seen
