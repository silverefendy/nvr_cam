"""Repository untuk operasi database terkait Camera."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.db.models.camera import Camera
from .base_repo import BaseRepository


class CameraRepository(BaseRepository[Camera]):
    def __init__(self, db: AsyncSession):
        super().__init__(Camera, db)

    async def get_active_cameras(self) -> list[Camera]:
        result = await self.db.execute(
            select(Camera).where(Camera.is_active == True).order_by(Camera.sort_order)
        )
        return result.scalars().all()

    async def get_by_drive(self, drive: str) -> list[Camera]:
        result = await self.db.execute(
            select(Camera).where(Camera.storage_drive == drive)
        )
        return result.scalars().all()

    async def get_motion_enabled(self) -> list[Camera]:
        result = await self.db.execute(
            select(Camera).where(Camera.motion_enabled == True, Camera.is_active == True)
        )
        return result.scalars().all()
