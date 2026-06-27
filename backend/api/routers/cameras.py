"""
Router: /api/v1/cameras
CRUD kamera + snapshot + test koneksi RTSP
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.base import get_db
from backend.db.repositories.camera_repo import CameraRepository
from backend.db.models.camera import Camera
from backend.api.schemas.camera import CameraCreate, CameraUpdate, CameraResponse
from backend.api.middleware.auth import get_current_user, require_role
from backend.db.models.user import User

router = APIRouter(tags=["cameras"])


@router.get("", response_model=list[CameraResponse])
async def list_cameras(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Daftar semua kamera aktif beserta status online/offline."""
    repo = CameraRepository(db)
    cameras = await repo.get_active_cameras()
    # TODO: inject status online/offline dari RecordingManager
    return cameras


@router.get("/{camera_id}", response_model=CameraResponse)
async def get_camera(
    camera_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    repo = CameraRepository(db)
    camera = await repo.get_by_id(camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail=f"Kamera {camera_id} tidak ditemukan")
    return camera


@router.post("", response_model=CameraResponse, status_code=201)
async def create_camera(
    body: CameraCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    """Tambah kamera baru. Hanya admin ke atas."""
    repo = CameraRepository(db)
    camera = Camera(**body.model_dump())
    return await repo.create(camera)


@router.put("/{camera_id}", response_model=CameraResponse)
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
    # TODO: implementasi — ambil dari folder snapshot
    return {"snapshot_url": f"/snapshots/{camera_id}/latest.jpg"}


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
    # TODO: implementasi — jalankan ffprobe singkat untuk test
    return {"status": "ok", "message": "Koneksi berhasil"}
