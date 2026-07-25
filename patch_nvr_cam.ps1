# =============================================================================
# patch_nvr_cam.ps1
# Jalankan dari root folder repo: cd C:\path\to\nvr_cam ; .\patch_nvr_cam.ps1
# =============================================================================

Write-Host "=== NVR CAM PATCH SCRIPT ===" -ForegroundColor Cyan
Write-Host "Memulai patch 4 file..." -ForegroundColor Yellow

# -----------------------------------------------------------------------------
# PATCH 1: backend/db/models/camera.py
# Tambah kolom status & last_seen yang hilang dari model tapi dipanggil di kode
# -----------------------------------------------------------------------------
Write-Host "`n[1/4] Patching backend/db/models/camera.py ..." -ForegroundColor Green

$cameraModel = @'
"""Camera model — registry semua kamera. Detail konfigurasi di config_json."""
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, Integer, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.db.base import Base


class Camera(Base):
    __tablename__ = "cameras"
    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    location: Mapped[str | None] = mapped_column(String(100))
    rtsp_main: Mapped[str] = mapped_column(String(500), nullable=False)
    rtsp_sub: Mapped[str | None] = mapped_column(String(500))
    storage_drive: Mapped[str] = mapped_column(String(50), nullable=False)
    motion_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    retention_days: Mapped[int] = mapped_column(Integer, default=30)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    config_json: Mapped[dict | None] = mapped_column(JSON)
    # FIX: kolom ini dipanggil di manager.py & cameras.py tapi sebelumnya
    # tidak ada di model — menyebabkan AttributeError saat update status.
    status: Mapped[str] = mapped_column(String(20), default="offline")
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    recordings: Mapped[list["Recording"]] = relationship(back_populates="camera", lazy="dynamic")
    motion_events: Mapped[list["MotionEvent"]] = relationship(back_populates="camera", lazy="dynamic")
'@

Set-Content -Path "backend\db\models\camera.py" -Value $cameraModel -Encoding UTF8
Write-Host "  OK: camera.py diupdate (tambah kolom status & last_seen)" -ForegroundColor White

# -----------------------------------------------------------------------------
# PATCH 2: backend/services/recorder/camera_recorder.py
# Bug utama: recording selesai TIDAK disimpan ke DB → halaman rekaman kosong
# Tambah: validasi storage_drive, simpan Recording ke DB tiap segment selesai
# -----------------------------------------------------------------------------
Write-Host "`n[2/4] Patching backend/services/recorder/camera_recorder.py ..." -ForegroundColor Green

$cameraRecorder = @'
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
"""
import asyncio
from pathlib import Path
from datetime import datetime, timezone
from backend.core.logging import get_logger
from .ffmpeg_wrapper import build_record_command, build_hls_command, detect_video_codec

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

    async def _save_recording_to_db(self, output_dir: Path, segment_started_at: datetime):
        """
        FIX UTAMA: Simpan metadata rekaman yang baru selesai ke tabel recordings.

        Sebelumnya fungsi ini tidak ada — FFmpeg menulis file ke disk tapi
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
                    # File masih kosong / sedang ditulis — skip
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

                # asyncio.create_subprocess_exec — tidak blocking event loop
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
                # Ini yang sebelumnya tidak ada — penyebab halaman rekaman kosong.
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
        - HEVC/H.265 → transcode ke H.264 (kompatibel hls.js di semua browser)
        - H.264 → stream copy (hemat CPU)

        File HLS lama dibersihkan sebelum FFmpeg baru dijalankan untuk
        menghindari konflik segment saat ganti IP/config kamera.
        """
        # Nama direktori harus cocok dengan yang diminta Nginx:
        # /hls/cam_01_sub/index.m3u8 → /var/lib/nvr_cam/hls/cam_01_sub/
        hls_dir = HLS_BASE_DIR / f"{self.camera_id}_sub"
        hls_dir.mkdir(parents=True, exist_ok=True)

        rtsp_url = self.camera.get("rtsp_sub") or self.camera["rtsp_main"]

        # Bersihkan file HLS lama sebelum start — penting saat ganti IP/config
        self._clear_hls_files(hls_dir)

        # Probe codec sekali saat pertama loop — run_in_executor agar tidak block
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
'@

Set-Content -Path "backend\services\recorder\camera_recorder.py" -Value $cameraRecorder -Encoding UTF8
Write-Host "  OK: camera_recorder.py diupdate (simpan rekaman ke DB + validasi storage)" -ForegroundColor White

# -----------------------------------------------------------------------------
# PATCH 3: backend/api/routers/cameras.py
# Bug: status selalu "offline" karena is_alive hanya cek proc recording,
#      bukan status DB. Tambah endpoint POST /import untuk import kamera batch.
# -----------------------------------------------------------------------------
Write-Host "`n[3/4] Patching backend/api/routers/cameras.py ..." -ForegroundColor Green

$camerasRouter = @'
"""
Router: /api/v1/cameras
CRUD kamera + snapshot + test koneksi RTSP + import batch
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.base import get_db
from backend.db.repositories.camera_repo import CameraRepository
from backend.db.models.camera import Camera
from backend.api.schemas.camera import CameraCreate, CameraUpdate, CameraResponse
from backend.api.middleware.auth import get_current_user, require_role
from backend.db.models.user import User
from backend.services.recorder.ffmpeg_wrapper import probe_stream

router = APIRouter(tags=["cameras"])


def _camera_to_dict(cam, recording_manager=None, camera_id: str = None) -> dict:
    """Helper: ubah objek Camera menjadi dict respons dengan status real-time.

    FIX: Status kini menggabungkan is_alive (proc FFmpeg) DAN cam.status (DB).
    Sebelumnya hanya pakai is_alive — langsung "offline" jika proc belum ready
    padahal kamera sebenarnya online (status DB sudah "online").
    """
    cid = camera_id or cam.id
    # Ambil status dari DB sebagai baseline
    db_status = getattr(cam, "status", "offline") or "offline"

    camera_dict = {
        "id": cam.id,
        "name": cam.name,
        "location": cam.location,
        "rtsp_main": cam.rtsp_main,
        "rtsp_sub": cam.rtsp_sub,
        "storage_drive": cam.storage_drive,
        "motion_enabled": cam.motion_enabled,
        "retention_days": cam.retention_days,
        "segment_duration": cam.config_json.get("segment_duration", 3600) if cam.config_json else 3600,
        "status": db_status,
        "is_active": cam.is_active,
        "sort_order": cam.sort_order,
        "config_json": cam.config_json,
        "last_seen": getattr(cam, "last_seen", None),
    }

    if recording_manager:
        is_proc_alive = recording_manager.get_status(cid)
        # Online jika proc hidup ATAU status DB sudah "online"
        is_online = is_proc_alive or (db_status == "online")
        camera_dict["is_online"] = is_online
        camera_dict["status"] = "online" if is_online else "offline"

    return camera_dict


@router.get("")
async def list_cameras(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Daftar semua kamera aktif beserta status online/offline."""
    repo = CameraRepository(db)
    cameras = await repo.get_active_cameras()
    recording_manager = request.app.state.recording_manager
    return [_camera_to_dict(cam, recording_manager) for cam in cameras]


@router.get("/{camera_id}")
async def get_camera(
    camera_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    repo = CameraRepository(db)
    camera = await repo.get_by_id(camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail=f"Kamera {camera_id} tidak ditemukan")
    recording_manager = request.app.state.recording_manager
    return _camera_to_dict(camera, recording_manager, camera_id)


@router.post("", status_code=201)
async def create_camera(
    body: CameraCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    """Tambah kamera baru. Hanya admin ke atas.
    Setelah kamera dibuat, recording langsung distart tanpa perlu restart server.
    """
    repo = CameraRepository(db)

    # Cek duplikasi ID
    existing = await repo.get_by_id(body.id)
    if existing:
        raise HTTPException(status_code=409, detail=f"Kamera dengan ID '{body.id}' sudah ada")

    camera = Camera(**body.model_dump())
    result = await repo.create(camera)

    # FIX: Start recorder untuk kamera baru tanpa perlu restart server
    try:
        recording_manager = request.app.state.recording_manager
        await recording_manager.restart_camera(body.id)
    except Exception as e:
        # Jangan gagalkan create jika recorder gagal start — log saja
        import logging
        logging.getLogger(__name__).warning(f"Kamera {body.id} dibuat tapi recorder gagal start: {e}")

    return result


@router.post("/import", status_code=201)
async def import_cameras(
    body: list[CameraCreate],
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    """Import beberapa kamera sekaligus dari JSON array.

    Contoh body:
    [
      {
        "id": "cam_01",
        "name": "Kamera Depan",
        "rtsp_main": "rtsp://admin:pass@192.168.1.100:554/stream1",
        "rtsp_sub": "rtsp://admin:pass@192.168.1.100:554/stream2",
        "storage_drive": "/mnt/driveA",
        "location": "Depan Kantor",
        "motion_enabled": false,
        "retention_days": 30
      }
    ]

    Kamera yang ID-nya sudah ada di DB akan di-skip (tidak error).
    Setelah import, recorder untuk kamera baru langsung distart.
    """
    if not body:
        raise HTTPException(status_code=400, detail="Daftar kamera tidak boleh kosong")

    repo = CameraRepository(db)
    recording_manager = request.app.state.recording_manager

    created = []
    skipped = []
    errors = []

    for cam_data in body:
        try:
            existing = await repo.get_by_id(cam_data.id)
            if existing:
                skipped.append(cam_data.id)
                continue

            camera = Camera(**cam_data.model_dump())
            result = await repo.create(camera)
            created.append(cam_data.id)

            # Start recorder untuk kamera baru
            try:
                await recording_manager.restart_camera(cam_data.id)
            except Exception as e:
                errors.append({"id": cam_data.id, "error": f"Recorder gagal start: {e}"})

        except Exception as e:
            errors.append({"id": cam_data.id, "error": str(e)})

    return {
        "imported": len(created),
        "skipped": len(skipped),
        "errors": len(errors),
        "created_ids": created,
        "skipped_ids": skipped,
        "error_details": errors,
    }


@router.put("/{camera_id}")
async def update_camera(
    camera_id: str,
    body: CameraUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    repo = CameraRepository(db)
    camera = await repo.get_by_id(camera_id)
    if not camera:
        raise HTTPException(status_code=404)
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(camera, field, value)
    await db.commit()
    await db.refresh(camera)

    # Restart recorder agar config baru langsung berlaku
    try:
        recording_manager = request.app.state.recording_manager
        await recording_manager.restart_camera(camera_id)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Update kamera {camera_id} OK, tapi recorder gagal restart: {e}")

    return camera


@router.delete("/{camera_id}", status_code=204)
async def delete_camera(
    camera_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    # Stop recorder sebelum hapus dari DB
    try:
        recording_manager = request.app.state.recording_manager
        if camera_id in recording_manager.recorders:
            await recording_manager.recorders[camera_id].stop()
            del recording_manager.recorders[camera_id]
    except Exception:
        pass

    repo = CameraRepository(db)
    deleted = await repo.delete_by_id(camera_id)
    if not deleted:
        raise HTTPException(status_code=404)


@router.get("/{camera_id}/snapshot")
async def get_snapshot(
    camera_id: str,
    _: User = Depends(get_current_user),
):
    """Ambil snapshot terbaru dari kamera (file JPG)."""
    return {"snapshot_url": f"/api/v1/stream/{camera_id}/snapshot.jpg"}


@router.post("/{camera_id}/test")
async def test_connection(
    camera_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    """Test apakah RTSP stream kamera bisa diakses.

    Catatan: test ini pakai ffprobe dengan timeout 10 detik.
    Jika berhasil di sini tapi live view tetap offline, kemungkinan penyebabnya:
    1. storage_drive tidak valid / volume Docker belum di-mount
    2. HLS dir tidak bisa ditulis (permission)
    3. Codec HEVC tapi transcode belum aktif
    Cek log backend untuk detail error FFmpeg.
    """
    repo = CameraRepository(db)
    camera = await repo.get_by_id(camera_id)
    if not camera:
        raise HTTPException(status_code=404)

    stream_info = probe_stream(camera.rtsp_main)

    if stream_info:
        # Ambil info codec dari hasil probe
        codec_info = None
        for stream in stream_info.get("streams", []):
            if stream.get("codec_type") == "video":
                codec_info = stream.get("codec_name")
                break

        return {
            "status": "success",
            "message": "Koneksi RTSP berhasil",
            "codec": codec_info,
            "note": "Jika live view masih offline, periksa log backend untuk error FFmpeg/storage.",
            "stream_info": stream_info,
        }
    else:
        return {
            "status": "failed",
            "message": "Tidak dapat terhubung ke kamera. Periksa URL RTSP, IP, username, dan password.",
        }
'@

Set-Content -Path "backend\api\routers\cameras.py" -Value $camerasRouter -Encoding UTF8
Write-Host "  OK: cameras.py diupdate (fix status + endpoint /import + auto-start recorder)" -ForegroundColor White

# -----------------------------------------------------------------------------
# PATCH 4: Alembic migration untuk kolom status & last_seen di tabel cameras
# -----------------------------------------------------------------------------
Write-Host "`n[4/4] Membuat Alembic migration untuk kolom status & last_seen ..." -ForegroundColor Green

# Buat file migration manual
$migrationDir = "backend\db\migrations\versions"
if (-not (Test-Path $migrationDir)) {
    New-Item -ItemType Directory -Path $migrationDir -Force | Out-Null
}

$migration = @'
"""add status and last_seen to cameras

Revision ID: a1b2c3d4e5f6
Revises: 
Create Date: 2026-07-25

Menambah kolom status dan last_seen ke tabel cameras.
Kolom ini dibutuhkan oleh manager.py (update_camera_status) dan cameras.py
tapi sebelumnya tidak ada di model maupun tabel DB.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'a1b2c3d4e5f6'
down_revision = None  # Ganti dengan revision sebelumnya jika ada
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Cek dulu apakah kolom sudah ada (aman dijalankan ulang)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_cols = [col['name'] for col in inspector.get_columns('cameras')]

    if 'status' not in existing_cols:
        op.add_column('cameras',
            sa.Column('status', sa.String(20), nullable=False, server_default='offline')
        )

    if 'last_seen' not in existing_cols:
        op.add_column('cameras',
            sa.Column('last_seen', sa.DateTime(timezone=True), nullable=True)
        )


def downgrade() -> None:
    op.drop_column('cameras', 'last_seen')
    op.drop_column('cameras', 'status')
'@

$migrationPath = "$migrationDir\a1b2c3d4e5f6_add_status_last_seen_cameras.py"
Set-Content -Path $migrationPath -Value $migration -Encoding UTF8
Write-Host "  OK: Migration dibuat di $migrationPath" -ForegroundColor White

# -----------------------------------------------------------------------------
# SELESAI
# -----------------------------------------------------------------------------
Write-Host "`n=============================================" -ForegroundColor Cyan
Write-Host " PATCH SELESAI. File yang diubah:" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  1. backend/db/models/camera.py" -ForegroundColor White
Write-Host "     -> Tambah kolom: status, last_seen" -ForegroundColor Gray
Write-Host "  2. backend/services/recorder/camera_recorder.py" -ForegroundColor White
Write-Host "     -> Simpan rekaman ke DB setelah FFmpeg selesai" -ForegroundColor Gray
Write-Host "     -> Validasi storage_drive sebelum start" -ForegroundColor Gray
Write-Host "  3. backend/api/routers/cameras.py" -ForegroundColor White
Write-Host "     -> Fix status online/offline" -ForegroundColor Gray
Write-Host "     -> Endpoint POST /api/v1/cameras/import (import batch)" -ForegroundColor Gray
Write-Host "     -> Auto-start recorder saat kamera baru dibuat/diupdate" -ForegroundColor Gray
Write-Host "  4. backend/db/migrations/versions/a1b2c3d4e5f6_add_status_last_seen_cameras.py" -ForegroundColor White
Write-Host "     -> Migration Alembic untuk kolom baru di tabel cameras" -ForegroundColor Gray

Write-Host "`n LANGKAH SELANJUTNYA:" -ForegroundColor Yellow
Write-Host " 1. Jalankan migration Alembic di server:" -ForegroundColor White
Write-Host "    docker exec -it nvr_backend alembic upgrade head" -ForegroundColor DarkYellow
Write-Host " 2. Push ke repo lalu restart container:" -ForegroundColor White
Write-Host "    git add -A && git commit -m 'fix: recording ke DB, status kamera, import batch'" -ForegroundColor DarkYellow
Write-Host "    git push" -ForegroundColor DarkYellow
Write-Host "    docker compose up -d --build backend" -ForegroundColor DarkYellow
Write-Host " 3. Untuk import kamera via API:" -ForegroundColor White
Write-Host "    POST /api/v1/cameras/import" -ForegroundColor DarkYellow
Write-Host '    Body: [{"id":"cam_01","name":"Kamera Depan","rtsp_main":"rtsp://...","storage_drive":"/mnt/driveA"}]' -ForegroundColor DarkYellow
Write-Host "`n PENTING: Pastikan volume storage di-mount di docker-compose.yml!" -ForegroundColor Red
Write-Host " Contoh: - /mnt/driveA:/mnt/driveA di bawah service backend" -ForegroundColor Gray
