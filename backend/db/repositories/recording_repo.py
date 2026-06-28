"""Repository untuk operasi database terkait Recording."""
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, delete
from backend.db.models.recording import Recording
from .base_repo import BaseRepository


class RecordingRepository(BaseRepository[Recording]):
    def __init__(self, db: AsyncSession):
        super().__init__(Recording, db)

    async def get_by_camera_and_date(
        self, camera_id: str, date_from: datetime, date_to: datetime
    ) -> list[Recording]:
        result = await self.db.execute(
            select(Recording).where(
                and_(
                    Recording.camera_id == camera_id,
                    Recording.started_at >= date_from,
                    Recording.started_at <= date_to,
                )
            ).order_by(Recording.started_at)
        )
        return result.scalars().all()

    async def get_oldest_unprotected(self, camera_id: str, limit: int = 10) -> list[Recording]:
        result = await self.db.execute(
            select(Recording).where(
                and_(
                    Recording.camera_id == camera_id,
                    Recording.is_protected == False,
                )
            ).order_by(Recording.started_at).limit(limit)
        )
        return result.scalars().all()

    async def get_total_size_mb(self, camera_id: str) -> float:
        result = await self.db.execute(
            select(func.sum(Recording.file_size_mb)).where(Recording.camera_id == camera_id)
        )
        return result.scalar() or 0.0

    async def get_not_encoded_av1(self, limit: int = 5) -> list[Recording]:
        """Ambil rekaman yang belum di-encode ke AV1 — untuk idle encoder."""
        result = await self.db.execute(
            select(Recording).where(
                and_(
                    Recording.is_encoded_av1 == False,
                    Recording.ended_at.isnot(None),
                )
            ).order_by(Recording.started_at).limit(limit)
        )
        return result.scalars().all()

    async def delete_old(self, camera_id: str, before_date: datetime) -> int:
        """Delete recordings older than specified date."""
        result = await self.db.execute(
            delete(Recording).where(
                and_(
                    Recording.camera_id == camera_id,
                    Recording.started_at < before_date,
                    Recording.is_protected == False,
                )
            )
        )
        await self.db.commit()
        return result.rowcount
