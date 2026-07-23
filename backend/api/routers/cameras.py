"""
Router: /api/v1/cameras
CRUD kamera + snapshot + test koneksi RTSP
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
    """Helper: ubah objek Camera menjadi dict respons dengan status real-time."""
    cid = camera_id or cam.id
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
        "status": "unknown",
        "is_active": cam.is_active,
        "sort_order": cam.sort_order,
        "config_json": cam.config_json,
        "last_seen": None,
    }
    if recording_manager:
        is_online = recording_manager.get_status(cid)
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
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    """Tambah kamera baru. Hanya admin ke atas."""
    repo = CameraRepository(db)
    camera = Camera(**body.model_dump())
    return await repo.create(camera)


@router.put("/{camera_id}")
async def update_camera(
    camera_id: str,
    body: CameraUpdate,
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
    return camera


@router.delete("/{camera_id}", status_code=204)
async def delete_camera(
    camera_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
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
    """Test apakah RTSP stream kamera bisa diakses."""
    repo = CameraRepository(db)
    camera = await repo.get_by_id(camera_id)
    if not camera:
        raise HTTPException(status_code=404)

    stream_info = probe_stream(camera.rtsp_main)

    if stream_info:
        return {
            "status": "success",
            "message": "Koneksi berhasil",
            "stream_info": stream_info,
        }
    else:
        return {
            "status": "failed",
            "message": "Tidak dapat terhubung ke kamera",
        }
