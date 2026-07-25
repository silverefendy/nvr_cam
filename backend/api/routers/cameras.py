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
    Sebelumnya hanya pakai is_alive â€” langsung "offline" jika proc belum ready
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
        # Jangan gagalkan create jika recorder gagal start â€” log saja
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
