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


@router.get("")
async def list_cameras(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Daftar semua kamera aktif beserta status online/offline."""
    repo = CameraRepository(db)
    cameras = await repo.get_active_cameras()
    
    # Inject live status from RecordingManager
    recording_manager = request.app.state.recording_manager
    result = []
    
    for cam in cameras:
        camera_dict = {
            "id": cam.id,
            "name": cam.name,
            "location": cam.location,
            "rtsp_main": cam.rtsp_main,
            "rtsp_sub": cam.rtsp_sub,
            "storage_drive": cam.storage_drive,
            "motion_enabled": cam.motion_enabled,
            "retention_days": cam.retention_days,
            "segment_duration": cam.segment_duration,
            "status": cam.status,
            "is_active": cam.is_active,
            "sort_order": cam.sort_order,
            "config_json": cam.config_json,
            "last_seen": cam.last_seen,
        }
        
        # Get real-time status from RecordingManager
        if recording_manager:
            is_online = recording_manager.get_status(cam.id)
            camera_dict["is_online"] = is_online
            if is_online:
                camera_dict["status"] = "online"
            else:
                camera_dict["status"] = "offline"
        
        result.append(camera_dict)
    
    return result


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
    
    camera_dict = {
        "id": camera.id,
        "name": camera.name,
        "location": camera.location,
        "rtsp_main": camera.rtsp_main,
        "rtsp_sub": camera.rtsp_sub,
        "storage_drive": camera.storage_drive,
        "motion_enabled": camera.motion_enabled,
        "retention_days": camera.retention_days,
        "segment_duration": camera.segment_duration,
        "status": camera.status,
        "is_active": camera.is_active,
        "sort_order": camera.sort_order,
        "config_json": camera.config_json,
        "last_seen": camera.last_seen,
    }
    
    # Get real-time status from RecordingManager
    recording_manager = request.app.state.recording_manager
    if recording_manager:
        is_online = recording_manager.get_status(camera_id)
        camera_dict["is_online"] = is_online
        if is_online:
            camera_dict["status"] = "online"
        else:
            camera_dict["status"] = "offline"
    
    return camera_dict


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
    # Return snapshot URL - actual file served by stream router
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
    
    # Test RTSP connection using ffprobe
    stream_info = probe_stream(camera.rtsp_main)
    
    if stream_info:
        return {
            "status": "success",
            "message": "Koneksi berhasil",
            "stream_info": stream_info
        }
    else:
        return {
            "status": "failed",
            "message": "Tidak dapat terhubung ke kamera"
        }
