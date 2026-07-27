from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.db.base import get_db
from backend.db.models.camera_group import CameraGroup
from backend.db.models.camera import Camera
from backend.api.schemas.camera_group import CameraGroupCreate, CameraGroupResponse, CameraAssignGroupRequest
from backend.api.middleware.auth import get_current_user, get_current_admin_user
from backend.db.models.user import User

router = APIRouter(tags=["camera-groups"])


@router.get("", response_model=list[CameraGroupResponse])
async def list_camera_groups(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """List semua grup kamera."""
    result = await db.execute(select(CameraGroup).order_by(CameraGroup.id))
    return result.scalars().all()


@router.post("", response_model=CameraGroupResponse, status_code=201)
async def create_camera_group(
    body: CameraGroupCreate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_admin_user),
):
    """Buat grup kamera baru (admin saja)."""
    group = CameraGroup(
        name=body.name,
        description=body.description,
        color=body.color,
    )
    db.add(group)
    await db.commit()
    await db.refresh(group)
    return group


@router.put("/{group_id}", response_model=CameraGroupResponse)
async def update_camera_group(
    group_id: int,
    body: CameraGroupCreate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_admin_user),
):
    """Update grup kamera (admin saja)."""
    result = await db.execute(select(CameraGroup).where(CameraGroup.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Grup kamera tidak ditemukan")

    group.name = body.name
    group.description = body.description
    group.color = body.color
    await db.commit()
    await db.refresh(group)
    return group


@router.delete("/{group_id}", status_code=204)
async def delete_camera_group(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_admin_user),
):
    """Hapus grup kamera (admin saja)."""
    result = await db.execute(select(CameraGroup).where(CameraGroup.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Grup kamera tidak ditemukan")

    await db.delete(group)
    await db.commit()


@router.put("/cameras/{camera_id}/group")
async def assign_camera_to_group(
    camera_id: str,
    body: CameraAssignGroupRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_admin_user),
):
    """Assign kamera ke grup (admin saja)."""
    # 1. Check camera
    result_cam = await db.execute(select(Camera).where(Camera.id == camera_id))
    camera = result_cam.scalar_one_or_none()
    if not camera:
        raise HTTPException(status_code=404, detail="Kamera tidak ditemukan")

    # 2. Check group if group_id is provided
    if body.group_id is not None:
        result_group = await db.execute(select(CameraGroup).where(CameraGroup.id == body.group_id))
        group = result_group.scalar_one_or_none()
        if not group:
            raise HTTPException(status_code=404, detail="Grup kamera tidak ditemukan")

    camera.group_id = body.group_id
    await db.commit()
    return {"message": f"Kamera {camera_id} berhasil dipetakan ke grup {body.group_id}"}
