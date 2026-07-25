"""
CameraRecorder â€” satu instance per kamera.
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
        # Waktu saat segment rekaman dimulai (beda dengan started_at yg di-set sekali)
        self._segment_started_at: datetime | None = None

    async def start(self):
        """Start recording dan HLS streaming secara concurrent (non-blocking)."""
        self.is_running = True
        self.started_at = datetime.now(timezone.utc)

        # FIX: Validasi storage_drive sebelum mulai agar error terdeteksi lebih awal
        # dan tidak loop reconnect diam-diam karena direktori tidak bisa dibuat.
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

        # Jalankan kedua loop secara concurrent tanpa blocking event loop
        await asyncio.gather(
            self._run_recording_loop(),
            self._run_hls_loop(),
            return_exceptions=True,
        )

    async def stop(self):
        """Stop semua proses FFmpeg dengan bersih."""
        self.is_running = False
        for proc in [self._record_proc, self._hls_proc]:
            if proc and proc.returncode is None:
                try:
                    proc.terminate()
                    await asyncio.wait_for(proc.wait(), timeout=10)
                except (asyncio.TimeoutError, ProcessLookupError):
                    try:
                        proc.kill()
                    except ProcessLookupError:
                        pass
        self._record_proc = None
        self._hls_proc = None

    def _clear_hls_files(self, hls_dir: Path):
        """
        Hapus semua file HLS lama (*.ts dan index.m3u8) sebelum FFmpeg baru start.
        Ini penting saat ganti IP/config â€” manifest lama mereferensikan
        segment dari RTSP sebelumnya yang menyebabkan error di FFmpeg baru.
        """
        try:
            for f in hls_dir.glob("*.ts"):
                f.unlink(missing_ok=True)
            for f in hls_dir.glob("*.m3u8"):
                f.unlink(missing_ok=True)
        except Exception as e:
            logger.warning(f"[{self.camera_id}] Gagal bersihkan file HLS lama: {e}")

    async def _save_recording_to_db(self, output_dir: Path, segment_started_at: datetime):
        """
        FIX UTAMA: Simpan metadata rekaman yang baru selesai ke tabel recordings.

        Sebelumnya fungsi ini tidak ada â€” FFmpeg menulis file ke disk tapi
        tidak ada entry di DB, sehingga halaman rekaman selalu kosong.

        Strategi: scan output_dir untuk file .mp4 yang belum terdaftar di DB,
        lalu insert. Ini aman jika dipanggil berkali-kali (unique constraint
        pada file_path mencegah duplikat).
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
                        continue  # Sudah ada, skip

                    stat = mp4_file.stat()
                    # File masih kosong / sedang ditulis â€” skip
                    if stat.st_size < 1024:
                        continue

                    duration_s = int((ended_at - segment_started_at).total_seconds())
                    rec = Recording(
                        camera_id=self.camera_id,
                        file_path=str(mp4_file),
                        file_size_mb=round(stat.st_size / (1024 * 1024), 2),
                        started_at=segment_started_at,
                        ended_at=ended_at,
                        duration_s=max(0, duration_s),
                        codec="H264",  # default; ffprobe jika diperlukan
                        is_protected=False,
                        is_encoded_av1=False,
                    )
                    db.add(rec)

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
                logger.info(f"[{self.camera_id}] Mulai recording")

                # Catat waktu mulai segment ini
                self._segment_started_at = datetime.now(timezone.utc)

                # asyncio.create_subprocess_exec â€” tidak blocking event loop
                self._record_proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.PIPE,
                )

                # Update status online
                manager = RecordingManager.get_instance()
                await manager.update_camera_status(self.camera_id, "online")
                self._last_seen = datetime.now(timezone.utc)

                # Tunggu FFmpeg selesai (non-blocking)
                _, stderr_bytes = await self._record_proc.communicate()
                if stderr_bytes:
                    last_err = stderr_bytes.decode(errors="replace").strip().splitlines()
                    if last_err:
                        logger.debug(f"[{self.camera_id}] FFmpeg stderr: {last_err[-1]}")

                # FIX: Simpan metadata rekaman ke DB setelah FFmpeg selesai/putus.
                # Ini yang sebelumnya tidak ada â€” penyebab halaman rekaman kosong.
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
                logger.error(f"[{self.camera_id}] Error recording loop: {e}")
                if self.is_running:
                    await asyncio.sleep(self._reconnect_delay)

    async def _run_hls_loop(self):
        """Loop HLS streaming untuk live view browser.

        Output ditulis ke /var/lib/nvr_cam/hls/<camera_id>_sub/
        sesuai dengan naming yang diharapkan Nginx dan frontend.

        Otomatis deteksi codec via ffprobe saat pertama start:
        - HEVC/H.265 â†’ transcode ke H.264 (kompatibel hls.js di semua browser)
        - H.264 â†’ stream copy (hemat CPU)

        File HLS lama dibersihkan sebelum FFmpeg baru dijalankan untuk
        menghindari konflik segment saat ganti IP/config kamera.
        """
        # Nama direktori harus cocok dengan yang diminta Nginx:
        # /hls/cam_01_sub/index.m3u8 â†’ /var/lib/nvr_cam/hls/cam_01_sub/
        hls_dir = HLS_BASE_DIR / f"{self.camera_id}_sub"
        hls_dir.mkdir(parents=True, exist_ok=True)

        rtsp_url = self.camera.get("rtsp_sub") or self.camera["rtsp_main"]

        # Bersihkan file HLS lama sebelum start â€” penting saat ganti IP/config
        self._clear_hls_files(hls_dir)

        # Probe codec sekali saat pertama loop â€” run_in_executor agar tidak block
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

                self._hls_proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.PIPE,
                )

                # Log stderr FFmpeg agar mudah debug
                _, stderr_bytes = await self._hls_proc.communicate()
                if stderr_bytes:
                    err_lines = stderr_bytes.decode(errors="replace").strip().splitlines()
                    if err_lines:
                        logger.warning(
                            f"[{self.camera_id}] HLS FFmpeg stderr: {err_lines[-1]}"
                        )

                if self.is_running:
                    logger.warning(f"[{self.camera_id}] HLS stream putus, retry dalam 5s")
                    await asyncio.sleep(5)

            except asyncio.CancelledError:
                break
            except Exception as e:
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
