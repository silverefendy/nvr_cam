"""
CameraRecorder — satu instance per kamera.
Mengelola FFmpeg process untuk recording dan HLS streaming.

Catatan implementasi:
- Pakai asyncio.create_subprocess_exec (BUKAN subprocess.Popen) agar tidak
  memblokir event loop FastAPI saat menunggu FFmpeg.
- HLS ditulis ke /var/lib/nvr_cam/hls/<camera_id>_sub/ agar Nginx bisa serve
  langsung dari volume hls_data yang di-mount di docker-compose.yml.
- Codec HEVC (H.265) dari kamera fisik tidak didukung hls.js di browser.
  Recorder otomatis deteksi codec via ffprobe dan aktifkan transcode ke H.264
  jika diperlukan.
- Saat recorder di-restart (ganti IP/config), file HLS lama dibersihkan dulu
  agar FFmpeg baru tidak baca manifest stale yang referensikan segment lama.
- File 0MB (rekaman gagal) dibersihkan otomatis setelah setiap segment selesai.
"""
import asyncio
from pathlib import Path
from datetime import datetime, timezone
from backend.core.logging import get_logger
from .ffmpeg_wrapper import build_record_command, build_hls_command, detect_video_codec, probe_codec_from_file

logger = get_logger(__name__, service="recorder")

# Path ini harus cocok dengan volume hls_data di docker-compose.yml
# dan dengan path yang di-serve Nginx: /var/lib/nvr_cam/hls/
HLS_BASE_DIR = Path("/var/lib/nvr_cam/hls")


class CameraRecorder:
    _active_ffmpeg_count = 0
    _active_ffmpeg_lock = asyncio.Lock()
    _max_active_ffmpeg = 30

    def __init__(self, camera: dict):
        self.camera = camera
        self.camera_id = camera["id"]
        self._record_proc: asyncio.subprocess.Process | None = None
        self._hls_proc: asyncio.subprocess.Process | None = None
        self.is_running = False
        self._reconnect_delay = 30
        self.current_file: str | None = None
        self.started_at: datetime | None = None
        self._last_seen: datetime | None = None
        self._segment_started_at: datetime | None = None
        self.last_error: str | None = None
        self._record_slot_acquired = False
        self._hls_slot_acquired = False

    @classmethod
    async def _wait_for_ffmpeg_slot(cls, camera_id: str):
        while True:
            async with cls._active_ffmpeg_lock:
                if cls._active_ffmpeg_count < cls._max_active_ffmpeg:
                    cls._active_ffmpeg_count += 1
                    return
                logger.warning(
                    f"[{camera_id}] FFmpeg aktif sudah {cls._active_ffmpeg_count}; menunggu slot kosong",
                    extra={"camera_id": camera_id, "action": "queue_ffmpeg"},
                )
            await asyncio.sleep(5)

    @classmethod
    async def _release_ffmpeg_slot(cls):
        async with cls._active_ffmpeg_lock:
            cls._active_ffmpeg_count = max(0, cls._active_ffmpeg_count - 1)

    @classmethod
    def active_ffmpeg_count(cls) -> int:
        return cls._active_ffmpeg_count

    async def start(self):
        """Start recording dan HLS streaming secara concurrent (non-blocking)."""
        self.is_running = True
        self.started_at = datetime.now(timezone.utc)

        drive = self.camera.get("storage_drive", "")
        if not drive:
            logger.error(f"[{self.camera_id}] storage_drive kosong! Periksa konfigurasi kamera di DB.")
            return
        try:
            Path(drive).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(
                f"[{self.camera_id}] Tidak bisa akses storage_drive '{drive}': {e}. "
                f"Pastikan path/volume sudah di-mount dengan benar di docker-compose.yml."
            )
            return

        await asyncio.gather(
            self._run_recording_loop(),
            self._run_hls_loop(),
            return_exceptions=True,
        )

    async def stop(self):
        """Stop semua proses FFmpeg dengan bersih."""
        self.is_running = False
        for proc, slot_attr in [
            (self._record_proc, "_record_slot_acquired"),
            (self._hls_proc, "_hls_slot_acquired"),
        ]:
            if proc and proc.returncode is None:
                try:
                    proc.terminate()
                    await asyncio.wait_for(proc.wait(), timeout=10)
                except (asyncio.TimeoutError, ProcessLookupError):
                    try:
                        proc.kill()
                    except ProcessLookupError:
                        pass
                if getattr(self, slot_attr):
                    await self._release_ffmpeg_slot()
                    setattr(self, slot_attr, False)
        self._record_proc = None
        self._hls_proc = None

    def _clear_hls_files(self, hls_dir: Path):
        """
        Hapus semua file HLS lama (*.ts dan index.m3u8) sebelum FFmpeg baru start.
        Ini penting saat ganti IP/config — manifest lama mereferensikan
        segment dari RTSP sebelumnya yang menyebabkan error di FFmpeg baru.
        """
        try:
            for f in hls_dir.glob("*.ts"):
                f.unlink(missing_ok=True)
            for f in hls_dir.glob("*.m3u8"):
                f.unlink(missing_ok=True)
        except Exception as e:
            logger.warning(f"[{self.camera_id}] Gagal bersihkan file HLS lama: {e}")

    def _cleanup_empty_files(self, output_dir: Path):
        """
        FIX: Hapus file MP4 0MB (rekaman gagal) dari disk.
        File 0MB terbentuk ketika FFmpeg crash/error sebelum write data apapun.
        Jika tidak dibersihkan, file ini akan menumpuk di storage dan
        muncul sebagai entry tanpa bisa diputar di halaman Playback.

        Dipanggil setelah setiap segment selesai.
        """
        try:
            cleaned = 0
            for mp4_file in output_dir.glob("*.mp4"):
                if mp4_file.stat().st_size < 1024:  # < 1KB = 0MB atau sangat kecil
                    mp4_file.unlink(missing_ok=True)
                    cleaned += 1
            if cleaned > 0:
                logger.info(f"[{self.camera_id}] Hapus {cleaned} file rekaman kosong dari {output_dir}")
        except Exception as e:
            logger.warning(f"[{self.camera_id}] Gagal cleanup file kosong: {e}")

    async def _save_recording_to_db(self, output_dir: Path, segment_started_at: datetime):
        """
        Simpan metadata rekaman yang baru selesai ke tabel recordings.
        File 0MB di-skip otomatis.
        """
        from backend.db.base import AsyncSessionLocal
        from backend.db.models.recording import Recording
        from sqlalchemy import select

        ended_at = datetime.now(timezone.utc)

        try:
            async with AsyncSessionLocal() as db:
                for mp4_file in sorted(output_dir.glob("*.mp4")):
                    # Cek apakah file ini sudah terdaftar
                    existing = await db.execute(
                        select(Recording).where(Recording.file_path == str(mp4_file))
                    )
                    if existing.scalar_one_or_none() is not None:
                        continue

                    stat = mp4_file.stat()
                    # File kosong / sedang ditulis — skip (akan dibersihkan oleh _cleanup_empty_files)
                    if stat.st_size < 1024:
                        continue

                    duration_s = int((ended_at - segment_started_at).total_seconds())

                    # Probe codec aktual dari file
                    loop = asyncio.get_event_loop()
                    codec_name = await loop.run_in_executor(
                        None, probe_codec_from_file, str(mp4_file)
                    )
                    if codec_name in ("hevc", "h265"):
                        codec_str = "H265"
                    else:
                        codec_str = "H264"

                    rec = Recording(
                        camera_id=self.camera_id,
                        file_path=str(mp4_file),
                        file_size_mb=round(stat.st_size / (1024 * 1024), 2),
                        started_at=segment_started_at,
                        ended_at=ended_at,
                        duration_s=max(0, duration_s),
                        codec=codec_str,
                        is_protected=False,
                        is_encoded_av1=False,
                    )
                    db.add(rec)
                    size_mb = stat.st_size / (1024 * 1024)
                    logger.info(
                        f"[REC] Segment tersimpan: {mp4_file}, size: {size_mb:.1f}MB",
                        extra={"camera_id": self.camera_id, "action": "segment_saved"},
                    )

                await db.commit()
                logger.info(f"[{self.camera_id}] Metadata rekaman disimpan ke DB")

        except Exception as e:
            logger.error(f"[{self.camera_id}] Gagal simpan rekaman ke DB: {e}")

    async def _run_recording_loop(self):
        """Loop recording 24/7 dengan auto-reconnect."""
        from backend.services.recorder.manager import RecordingManager

        while self.is_running:
            try:
                output_dir = self._get_output_dir()
                output_dir.mkdir(parents=True, exist_ok=True)
                output_pattern = str(output_dir / "%H-%M-%S.mp4")

                cmd = build_record_command(self.camera["rtsp_main"], output_pattern)
                logger.info(
                    f"[REC] Camera {self.camera_id} mulai rekam ke {self.camera.get('storage_drive')}",
                    extra={"camera_id": self.camera_id, "action": "start"},
                )

                self._segment_started_at = datetime.now(timezone.utc)

                await self._wait_for_ffmpeg_slot(self.camera_id)
                self._record_slot_acquired = True
                self._record_proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.PIPE,
                )
                logger.info(
                    f"[{self.camera_id}] FFmpeg recording started pid={self._record_proc.pid}",
                    extra={"camera_id": self.camera_id, "pid": self._record_proc.pid, "action": "start"},
                )

                manager = RecordingManager.get_instance()
                await manager.update_camera_status(self.camera_id, "online")
                self._last_seen = datetime.now(timezone.utc)

                _, stderr_bytes = await self._record_proc.communicate()
                if self._record_slot_acquired:
                    await self._release_ffmpeg_slot()
                    self._record_slot_acquired = False
                if stderr_bytes:
                    last_err = stderr_bytes.decode(errors="replace").strip().splitlines()
                    if last_err:
                        self.last_error = last_err[-1]
                        logger.error(
                            f"[{self.camera_id}] FFmpeg exited code={self._record_proc.returncode}: {self.last_error}",
                            extra={
                                "camera_id": self.camera_id,
                                "pid": self._record_proc.pid,
                                "action": "crash",
                            },
                        )
                        manager.record_error(self.camera_id, self.last_error)
                elif self._record_proc.returncode not in (0, None):
                    self.last_error = f"FFmpeg exited with code {self._record_proc.returncode}"
                    logger.error(
                        f"[{self.camera_id}] {self.last_error}",
                        extra={
                            "camera_id": self.camera_id,
                            "pid": self._record_proc.pid,
                            "action": "crash",
                        },
                    )
                    manager.record_error(self.camera_id, self.last_error)

                # Cleanup file 0MB SEBELUM simpan ke DB
                self._cleanup_empty_files(output_dir)

                # Simpan metadata rekaman ke DB setelah FFmpeg selesai/putus
                if self._segment_started_at:
                    await self._save_recording_to_db(output_dir, self._segment_started_at)

                if self.is_running:
                    logger.warning(
                        f"[{self.camera_id}] FFmpeg mati, reconnect dalam {self._reconnect_delay}s"
                    )
                    await manager.update_camera_status(self.camera_id, "offline")
                    await asyncio.sleep(self._reconnect_delay)

            except asyncio.CancelledError:
                break
            except Exception as e:
                if self._record_slot_acquired:
                    await self._release_ffmpeg_slot()
                    self._record_slot_acquired = False
                self.last_error = str(e)
                RecordingManager.get_instance().record_error(self.camera_id, self.last_error)
                logger.error(f"[{self.camera_id}] Error recording loop: {e}")
                if self.is_running:
                    await asyncio.sleep(self._reconnect_delay)

    async def _run_hls_loop(self):
        """Loop HLS streaming untuk live view browser."""
        hls_dir = HLS_BASE_DIR / f"{self.camera_id}_sub"
        hls_dir.mkdir(parents=True, exist_ok=True)

        rtsp_url = self.camera.get("rtsp_sub") or self.camera["rtsp_main"]

        # Bersihkan file HLS lama sebelum start
        self._clear_hls_files(hls_dir)

        loop = asyncio.get_event_loop()
        codec = await loop.run_in_executor(None, detect_video_codec, rtsp_url)
        force_transcode = codec in ("hevc", "h265")

        if force_transcode:
            logger.info(
                f"[{self.camera_id}] Codec HEVC terdeteksi ({codec!r}) "
                f"-> aktifkan transcode H.264 untuk kompatibilitas browser"
            )
        else:
            logger.info(
                f"[{self.camera_id}] Codec: {codec or 'unknown'} -> stream copy (tanpa transcode)"
            )

        while self.is_running:
            try:
                cmd = build_hls_command(
                    rtsp_url,
                    str(hls_dir),
                    force_transcode=force_transcode,
                )

                await self._wait_for_ffmpeg_slot(self.camera_id)
                self._hls_slot_acquired = True
                self._hls_proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.PIPE,
                )
                logger.info(
                    f"[{self.camera_id}] FFmpeg HLS started pid={self._hls_proc.pid}",
                    extra={"camera_id": self.camera_id, "pid": self._hls_proc.pid, "action": "start"},
                )

                _, stderr_bytes = await self._hls_proc.communicate()
                if self._hls_slot_acquired:
                    await self._release_ffmpeg_slot()
                    self._hls_slot_acquired = False
                if stderr_bytes:
                    err_lines = stderr_bytes.decode(errors="replace").strip().splitlines()
                    if err_lines:
                        self.last_error = err_lines[-1]
                        logger.warning(
                            f"[{self.camera_id}] HLS FFmpeg exited code={self._hls_proc.returncode}: {self.last_error}",
                            extra={
                                "camera_id": self.camera_id,
                                "pid": self._hls_proc.pid,
                                "action": "crash",
                            },
                        )
                        from backend.services.recorder.manager import RecordingManager
                        RecordingManager.get_instance().record_error(self.camera_id, self.last_error)
                elif self._hls_proc.returncode not in (0, None):
                    self.last_error = f"HLS FFmpeg exited with code {self._hls_proc.returncode}"
                    logger.warning(
                        f"[{self.camera_id}] {self.last_error}",
                        extra={
                            "camera_id": self.camera_id,
                            "pid": self._hls_proc.pid,
                            "action": "crash",
                        },
                    )
                    from backend.services.recorder.manager import RecordingManager
                    RecordingManager.get_instance().record_error(self.camera_id, self.last_error)

                if self.is_running:
                    logger.warning(f"[{self.camera_id}] HLS stream putus, retry dalam 5s")
                    await asyncio.sleep(5)

            except asyncio.CancelledError:
                break
            except Exception as e:
                if self._hls_slot_acquired:
                    await self._release_ffmpeg_slot()
                    self._hls_slot_acquired = False
                self.last_error = str(e)
                from backend.services.recorder.manager import RecordingManager
                RecordingManager.get_instance().record_error(self.camera_id, self.last_error)
                logger.error(f"[{self.camera_id}] Error HLS loop: {e}")
                if self.is_running:
                    await asyncio.sleep(10)

    def _get_output_dir(self) -> Path:
        drive = self.camera["storage_drive"]
        date_str = datetime.now().strftime("%Y-%m-%d")
        return Path(drive) / self.camera_id / date_str

    @property
    def is_alive(self) -> bool:
        """True jika proses recording FFmpeg sedang aktif."""
        return (
            self._record_proc is not None
            and self._record_proc.returncode is None
        )

    @property
    def last_seen(self) -> datetime | None:
        return self._last_seen

    @property
    def segment_started_at(self) -> datetime | None:
        return self._segment_started_at

    @property
    def recording_pid(self) -> int | None:
        if self._record_proc and self._record_proc.returncode is None:
            return self._record_proc.pid
        return None
