"""
Router: /api/v1/cameras
CRUD kamera + snapshot + test koneksi RTSP + import batch
+ stream-ready polling endpoint
+ ONVIF camera settings (FPS, bitrate, resolution, codec)
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path
import time, subprocess, logging
from datetime import datetime, timezone
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional

from backend.db.base import get_db
from backend.db.repositories.camera_repo import CameraRepository
from backend.db.models.camera import Camera
from backend.api.schemas.camera import CameraCreate, CameraUpdate, CameraResponse
from backend.api.middleware.auth import get_current_user, require_role
from backend.db.models.user import User
from backend.services.recorder.ffmpeg_wrapper import probe_stream
from backend.services.audit import write_audit_log

logger = logging.getLogger(__name__)

router = APIRouter(tags=["cameras"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ONVIFSettings(BaseModel):
    fps: Optional[int] = None            # 1-30
    bitrate_kbps: Optional[int] = None   # kbps, e.g. 2048
    width: Optional[int] = None          # e.g. 1920
    height: Optional[int] = None         # e.g. 1080
    codec: Optional[str] = None          # "H264" | "H265"
    username: Optional[str] = None
    password: Optional[str] = None


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _camera_to_dict(cam, recording_manager=None, camera_id: str = None) -> dict:
    cid = camera_id or cam.id
    db_status = getattr(cam, "status", "offline") or "offline"

    camera_dict = {
        "id": cam.id,
        "name": cam.name,
        "location": cam.location,
        "rtsp_main": cam.rtsp_main,
        "rtsp_sub": cam.rtsp_sub,
        "rtsp_url_main": cam.rtsp_url_main,
        "rtsp_url_sub": cam.rtsp_url_sub,
        "storage_drive": cam.storage_drive,
        "motion_enabled": cam.motion_enabled,
        "retention_days": cam.retention_days,
        "segment_duration": cam.config_json.get("segment_duration", 1800) if cam.config_json else 1800,
        "status": db_status,
        "is_active": cam.is_active,
        "sort_order": cam.sort_order,
        "config_json": cam.config_json,
        "recording_schedule": cam.recording_schedule,
        "schedule_start_time": cam.schedule_start_time,
        "schedule_end_time": cam.schedule_end_time,
        "schedule_days": cam.schedule_days,
        "group_id": cam.group_id,
        "last_seen": getattr(cam, "last_seen", None),
    }

    if recording_manager:
        is_proc_alive = recording_manager.get_status(cid)
        is_online = is_proc_alive or (db_status == "online")
        camera_dict["is_online"] = is_online
        camera_dict["status"] = "online" if is_online else "offline"

    return camera_dict


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

@router.get("")
async def list_cameras(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
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
    current_user: User = Depends(require_role("admin")),
):
    repo = CameraRepository(db)
    existing = await repo.get_by_id(body.id)
    if existing:
        raise HTTPException(status_code=409, detail=f"Kamera dengan ID '{body.id}' sudah ada")

    # Default segment_duration ke 1800 (30 menit) jika belum diset
    data = body.model_dump()
    if "config_json" not in data or not data["config_json"]:
        data["config_json"] = {}
    if "segment_duration" not in data["config_json"]:
        data["config_json"]["segment_duration"] = 1800

    camera = Camera(**data)
    result = await repo.create(camera)

    try:
        recording_manager = request.app.state.recording_manager
        await recording_manager.restart_camera(body.id)
    except Exception as e:
        logger.warning(f"Kamera {body.id} dibuat tapi recorder gagal start: {e}")

    await write_audit_log(
        db, action="camera.create", user_id=current_user.id,
        target_type="camera", target_id=body.id,
        detail={"name": body.name},
        ip_address=request.client.host if request.client else None,
    )
    return result


@router.post("/import", status_code=201)
async def import_cameras(
    body: list[CameraCreate],
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    if not body:
        raise HTTPException(status_code=400, detail="Daftar kamera tidak boleh kosong")

    repo = CameraRepository(db)
    recording_manager = request.app.state.recording_manager
    created, skipped, errors = [], [], []

    for cam_data in body:
        try:
            existing = await repo.get_by_id(cam_data.id)
            if existing:
                skipped.append(cam_data.id)
                continue
            camera = Camera(**cam_data.model_dump())
            await repo.create(camera)
            created.append(cam_data.id)
            try:
                await recording_manager.restart_camera(cam_data.id)
            except Exception as e:
                errors.append({"id": cam_data.id, "error": f"Recorder gagal start: {e}"})
            await write_audit_log(
                db, action="camera.create", user_id=current_user.id,
                target_type="camera", target_id=cam_data.id,
                detail={"source": "import", "name": cam_data.name},
                ip_address=request.client.host if request.client else None,
            )
        except Exception as e:
            errors.append({"id": cam_data.id, "error": str(e)})

    return {
        "imported": len(created), "skipped": len(skipped), "errors": len(errors),
        "created_ids": created, "skipped_ids": skipped, "error_details": errors,
    }


@router.put("/{camera_id}")
async def update_camera(
    camera_id: str,
    body: CameraUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    repo = CameraRepository(db)
    camera = await repo.get_by_id(camera_id)
    if not camera:
        raise HTTPException(status_code=404)

    update_data = body.model_dump(exclude_none=True)

    # Tangani segment_duration: simpan ke config_json
    if "segment_duration" in update_data:
        seg = update_data.pop("segment_duration")
        if camera.config_json is None:
            camera.config_json = {}
        camera.config_json["segment_duration"] = seg
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(camera, "config_json")

    for field, value in update_data.items():
        setattr(camera, field, value)

    await db.commit()
    await db.refresh(camera)

    try:
        recording_manager = request.app.state.recording_manager
        await recording_manager.restart_camera(camera_id)
    except Exception as e:
        logger.warning(f"Update kamera {camera_id} OK, tapi recorder gagal restart: {e}")

    await write_audit_log(
        db, action="camera.update", user_id=current_user.id,
        target_type="camera", target_id=camera_id,
        ip_address=request.client.host if request.client else None,
    )
    return camera


@router.delete("/{camera_id}", status_code=204)
async def delete_camera(
    camera_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    try:
        recording_manager = request.app.state.recording_manager
        if camera_id in recording_manager.recorders:
            await recording_manager.recorders[camera_id].stop()
            del recording_manager.recorders[camera_id]
        storage_manager = getattr(recording_manager, "storage_manager", None)
        if storage_manager is not None:
            storage_manager.remove_camera(camera_id)
    except Exception:
        pass

    repo = CameraRepository(db)
    deleted = await repo.delete_by_id(camera_id)
    if not deleted:
        raise HTTPException(status_code=404)
    await write_audit_log(
        db, action="camera.delete", user_id=current_user.id,
        target_type="camera", target_id=camera_id,
        ip_address=request.client.host if request.client else None,
    )


# ---------------------------------------------------------------------------
# Stream-ready polling
# ---------------------------------------------------------------------------

@router.get("/{camera_id}/stream-ready")
async def check_stream_ready(
    camera_id: str,
    stream_type: str = "sub",
    _: User = Depends(get_current_user),
):
    """
    Cek apakah HLS stream kamera sudah siap (file .m3u8 ada dan segment pertama tersedia).
    Frontend polling endpoint ini setelah add camera agar tidak tampilkan video hitam.
    Return: {ready: bool, hls_path: str}
    """
    hls_base = Path("/var/lib/nvr_cam/hls")
    # Coba main dan sub tergantung stream_type
    candidates = [
        hls_base / camera_id / f"{stream_type}.m3u8",
        hls_base / camera_id / "sub.m3u8",
        hls_base / camera_id / "main.m3u8",
        hls_base / camera_id / "index.m3u8",
        hls_base / camera_id / "stream.m3u8",
    ]
    for m3u8 in candidates:
        if m3u8.exists() and m3u8.stat().st_size > 0:
            # Pastikan minimal ada 1 segment .ts
            ts_files = list(m3u8.parent.glob("*.ts"))
            if ts_files:
                return {"ready": True, "hls_path": str(m3u8)}
    return {"ready": False, "hls_path": None}


# ---------------------------------------------------------------------------
# Storage stats per camera
# ---------------------------------------------------------------------------

@router.get("/{camera_id}/storage-stats")
async def get_camera_storage_stats(
    camera_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    Hitung statistik penggunaan storage untuk satu kamera:
    - total_gb_used: total GB rekaman
    - file_count: jumlah file rekaman
    - avg_gb_per_day: rata-rata GB/hari dari data aktual
    - estimated_gb_per_month: proyeksi GB/bulan
    - avg_gb_per_hour: rata-rata GB/jam (per segment)
    """
    from backend.db.base import AsyncSessionLocal
    from sqlalchemy import text

    try:
        async with AsyncSessionLocal() as session:
            # Ambil info kamera
            repo = CameraRepository(session)
            camera = await repo.get_by_id(camera_id)
            if not camera:
                raise HTTPException(status_code=404, detail="Kamera tidak ditemukan")

            # Query rekaman dari DB
            result = await session.execute(
                text("""
                    SELECT
                        COUNT(*) as file_count,
                        COALESCE(SUM(file_size), 0) as total_bytes,
                        MIN(start_time) as oldest,
                        MAX(end_time) as newest
                    FROM recordings
                    WHERE camera_id = :cam_id AND is_deleted = false AND file_size > 0
                """),
                {"cam_id": camera_id}
            )
            row = result.fetchone()

            file_count = row.file_count or 0
            total_bytes = row.total_bytes or 0
            total_gb = total_bytes / (1024 ** 3)

            # Hitung rata-rata per hari
            avg_gb_per_day = 0.0
            avg_gb_per_hour = 0.0
            if row.oldest and row.newest and file_count > 0:
                span_seconds = (row.newest - row.oldest).total_seconds()
                span_days = max(span_seconds / 86400, 1)
                avg_gb_per_day = total_gb / span_days
                avg_gb_per_hour = total_gb / max(span_seconds / 3600, 1)

            return {
                "camera_id": camera_id,
                "camera_name": camera.name,
                "storage_drive": camera.storage_drive,
                "file_count": file_count,
                "total_gb_used": round(total_gb, 3),
                "total_mb_used": round(total_gb * 1024, 1),
                "avg_gb_per_day": round(avg_gb_per_day, 3),
                "avg_gb_per_hour": round(avg_gb_per_hour, 4),
                "estimated_gb_per_month": round(avg_gb_per_day * 30, 1),
                "data_span_days": round((row.newest - row.oldest).total_seconds() / 86400, 1) if row.oldest and row.newest else 0,
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"storage-stats error for {camera_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/storage-stats/all")
async def get_all_cameras_storage_stats(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    Statistik storage untuk semua kamera sekaligus.
    Return: [{camera_id, camera_name, total_gb_used, avg_gb_per_day, estimated_gb_per_month, ...}]
    """
    from backend.db.base import AsyncSessionLocal
    from sqlalchemy import text

    async with AsyncSessionLocal() as session:
        repo = CameraRepository(session)
        cameras = await repo.get_active_cameras()

        result = await session.execute(
            text("""
                SELECT
                    camera_id,
                    COUNT(*) as file_count,
                    COALESCE(SUM(file_size), 0) as total_bytes,
                    MIN(start_time) as oldest,
                    MAX(end_time) as newest
                FROM recordings
                WHERE is_deleted = false AND file_size > 0
                GROUP BY camera_id
            """)
        )
        rows = {r.camera_id: r for r in result.fetchall()}

        stats = []
        for cam in cameras:
            row = rows.get(cam.id)
            if not row:
                stats.append({
                    "camera_id": cam.id, "camera_name": cam.name,
                    "storage_drive": cam.storage_drive,
                    "file_count": 0, "total_gb_used": 0,
                    "avg_gb_per_day": 0, "estimated_gb_per_month": 0,
                })
                continue

            total_gb = row.total_bytes / (1024 ** 3)
            avg_gb_per_day = 0.0
            if row.oldest and row.newest:
                span_days = max((row.newest - row.oldest).total_seconds() / 86400, 1)
                avg_gb_per_day = total_gb / span_days

            stats.append({
                "camera_id": cam.id,
                "camera_name": cam.name,
                "storage_drive": cam.storage_drive,
                "file_count": row.file_count,
                "total_gb_used": round(total_gb, 3),
                "avg_gb_per_day": round(avg_gb_per_day, 3),
                "estimated_gb_per_month": round(avg_gb_per_day * 30, 1),
            })

        return stats


# ---------------------------------------------------------------------------
# ONVIF camera settings (FPS / bitrate / resolution / codec)
# ---------------------------------------------------------------------------

@router.get("/{camera_id}/onvif-settings")
async def get_onvif_settings(
    camera_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    """
    Baca konfigurasi encoder kamera saat ini via ONVIF.
    Return: {fps, bitrate_kbps, width, height, codec, profile_token}
    """
    repo = CameraRepository(db)
    camera = await repo.get_by_id(camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="Kamera tidak ditemukan")

    try:
        from onvif import ONVIFCamera
        ip = camera.ip_address or _extract_ip(camera.rtsp_main)
        username = camera.username or "admin"
        password = camera.password or ""

        cam = ONVIFCamera(ip, 80, username, password)
        await cam.update_xaddrs()
        media = await cam.create_media_service()
        profiles = await media.GetProfiles()

        if not profiles:
            raise HTTPException(status_code=404, detail="Tidak ada profile ONVIF ditemukan")

        profile = profiles[0]
        token = profile.token
        enc = profile.VideoEncoderConfiguration

        return {
            "profile_token": token,
            "codec": enc.Encoding if enc else None,
            "width": enc.Resolution.Width if enc and enc.Resolution else None,
            "height": enc.Resolution.Height if enc and enc.Resolution else None,
            "fps": enc.RateControl.FrameRateLimit if enc and enc.RateControl else None,
            "bitrate_kbps": enc.RateControl.BitrateLimit if enc and enc.RateControl else None,
            "quality": enc.Quality if enc else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ONVIF get settings error for {camera_id}: {e}")
        raise HTTPException(status_code=502, detail=f"Gagal membaca setting ONVIF: {e}")


@router.put("/{camera_id}/onvif-settings")
async def set_onvif_settings(
    camera_id: str,
    body: ONVIFSettings,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
    request: Request = None,
):
    """
    Kirim setting encoder ke kamera via ONVIF.
    Setelah berhasil, stream kamera akan di-restart.
    Field yang None tidak diubah.
    """
    repo = CameraRepository(db)
    camera = await repo.get_by_id(camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="Kamera tidak ditemukan")

    try:
        from onvif import ONVIFCamera
        ip = camera.ip_address or _extract_ip(camera.rtsp_main)
        username = body.username or camera.username or "admin"
        password = body.password or camera.password or ""

        cam = ONVIFCamera(ip, 80, username, password)
        await cam.update_xaddrs()
        media = await cam.create_media_service()
        profiles = await media.GetProfiles()

        if not profiles:
            raise HTTPException(status_code=404, detail="Tidak ada profile ONVIF ditemukan")

        profile = profiles[0]
        token = profile.token
        enc = profile.VideoEncoderConfiguration
        enc_token = enc.token

        # Baca konfigurasi encoder yang ada, lalu update field yang diminta
        request_body = media.create_type("SetVideoEncoderConfiguration")
        request_body.Configuration = enc
        request_body.ForcePersistence = True

        if body.fps is not None:
            enc.RateControl.FrameRateLimit = body.fps
        if body.bitrate_kbps is not None:
            enc.RateControl.BitrateLimit = body.bitrate_kbps
        if body.width is not None and body.height is not None:
            enc.Resolution.Width = body.width
            enc.Resolution.Height = body.height
        if body.codec is not None:
            enc.Encoding = body.codec

        await media.SetVideoEncoderConfiguration(request_body)

        # Restart stream agar perubahan langsung berlaku
        if request:
            try:
                recording_manager = request.app.state.recording_manager
                await recording_manager.restart_camera(camera_id)
            except Exception as re:
                logger.warning(f"ONVIF settings applied, tapi recorder gagal restart: {re}")

        await write_audit_log(
            db, action="camera.onvif_settings", user_id=current_user.id,
            target_type="camera", target_id=camera_id,
            detail={"fps": body.fps, "bitrate_kbps": body.bitrate_kbps,
                    "width": body.width, "height": body.height, "codec": body.codec},
            ip_address=request.client.host if request and request.client else None,
        )

        return {"status": "ok", "message": "Setting ONVIF berhasil diterapkan ke kamera"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ONVIF set settings error for {camera_id}: {e}")
        raise HTTPException(status_code=502, detail=f"Gagal mengirim setting ONVIF: {e}")


def _extract_ip(rtsp_url: str) -> str:
    """Ekstrak IP dari URL RTSP: rtsp://user:pass@192.168.1.x:554/..."""
    import re
    m = re.search(r"@([\d.]+)", rtsp_url or "")
    return m.group(1) if m else ""


# ---------------------------------------------------------------------------
# Snapshot endpoints
# ---------------------------------------------------------------------------

@router.get("/{camera_id}/snapshot")
async def get_snapshot(
    camera_id: str,
    _: User = Depends(get_current_user),
):
    return {"snapshot_url": f"/api/v1/stream/{camera_id}/snapshot.jpg"}


@router.post("/{camera_id}/test")
async def test_connection(
    camera_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    repo = CameraRepository(db)
    camera = await repo.get_by_id(camera_id)
    if not camera:
        raise HTTPException(status_code=404)

    stream_info = probe_stream(camera.rtsp_main)
    if stream_info:
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
            "message": "Tidak dapat terhubung ke kamera.",
        }


@router.post("/{camera_id}/snapshot")
async def take_manual_snapshot(
    camera_id: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    repo = CameraRepository(db)
    camera = await repo.get_by_id(camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="Kamera tidak ditemukan")

    rtsp_url = camera.rtsp_url_sub or camera.rtsp_sub or camera.rtsp_url_main or camera.rtsp_main
    if not rtsp_url:
        raise HTTPException(status_code=400, detail="URL RTSP kamera tidak tersedia")

    snapshot_dir = Path("/var/lib/nvr_cam/snapshots")
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    timestamp = int(time.time())
    filename = f"{camera_id}_{timestamp}.jpg"
    output_path = snapshot_dir / filename

    cmd = ["ffmpeg", "-y", "-rtsp_transport", "tcp", "-i", rtsp_url,
           "-vframes", "1", "-q:v", "2", str(output_path)]
    try:
        subprocess.run(cmd, timeout=15, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Gagal mengambil snapshot: FFmpeg timeout")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal mengambil snapshot: {e}")

    if not output_path.exists():
        raise HTTPException(status_code=500, detail="Gagal menyimpan snapshot")

    url = f"/api/v1/cameras/{camera_id}/snapshots/{filename}"
    return {
        "url": url, "filename": filename,
        "timestamp": datetime.fromtimestamp(timestamp, timezone.utc).isoformat()
    }


@router.get("/{camera_id}/snapshots")
async def list_manual_snapshots(camera_id: str, _user: User = Depends(get_current_user)):
    snapshot_dir = Path("/var/lib/nvr_cam/snapshots")
    if not snapshot_dir.exists():
        return []
    snapshots = []
    for f in sorted(snapshot_dir.glob(f"{camera_id}_*.jpg"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            ts = int(f.stem.split("_")[-1])
            dt = datetime.fromtimestamp(ts, timezone.utc).isoformat()
        except Exception:
            dt = datetime.fromtimestamp(f.stat().st_mtime, timezone.utc).isoformat()
        snapshots.append({
            "filename": f.name,
            "url": f"/api/v1/cameras/{camera_id}/snapshots/{f.name}",
            "timestamp": dt,
            "size_bytes": f.stat().st_size,
        })
    return snapshots


@router.get("/{camera_id}/snapshots/{filename}")
async def serve_manual_snapshot_file(
    camera_id: str, filename: str, _user: User = Depends(get_current_user)
):
    snapshot_dir = Path("/var/lib/nvr_cam/snapshots")
    file_path = snapshot_dir / filename
    if not file_path.resolve().is_relative_to(snapshot_dir.resolve()):
        raise HTTPException(status_code=400, detail="Path tidak valid")
    if not file_path.exists() or not filename.startswith(f"{camera_id}_"):
        raise HTTPException(status_code=404, detail="File snapshot tidak ditemukan")
    return FileResponse(file_path, media_type="image/jpeg")


@router.delete("/{camera_id}/snapshots/{filename}", status_code=204)
async def delete_manual_snapshot(
    camera_id: str, filename: str, _user: User = Depends(get_current_user)
):
    snapshot_dir = Path("/var/lib/nvr_cam/snapshots")
    file_path = snapshot_dir / filename
    if not file_path.resolve().is_relative_to(snapshot_dir.resolve()):
        raise HTTPException(status_code=400, detail="Path tidak valid")
    if not file_path.exists() or not filename.startswith(f"{camera_id}_"):
        raise HTTPException(status_code=404, detail="File snapshot tidak ditemukan")
    file_path.unlink()
