"""Repository untuk operasi database terkait MotionEvent."""
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from backend.db.models.motion_event import MotionEvent
from .base_repo import BaseRepository


class EventRepository(BaseRepository[MotionEvent]):
    def __init__(self, db: AsyncSession):
        super().__init__(MotionEvent, db)

    async def get_by_camera_and_date(
        self, camera_id: str, date_from: datetime, date_to: datetime
    ) -> list[MotionEvent]:
        result = await self.db.execute(
            select(MotionEvent).where(
                and_(
                    MotionEvent.camera_id == camera_id,
                    MotionEvent.started_at >= date_from,
                    MotionEvent.started_at <= date_to,
                )
            ).order_by(MotionEvent.started_at.desc())
        )
        return result.scalars().all()

    async def get_unnotified(self) -> list[MotionEvent]:
        result = await self.db.execute(
            select(MotionEvent).where(MotionEvent.notified == False)
        )
        return result.scalars().all()

    async def get_count_today(self, camera_id: str) -> int:
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        result = await self.db.execute(
            select(func.count(MotionEvent.id)).where(
                and_(MotionEvent.camera_id == camera_id, MotionEvent.started_at >= today)
            )
        )
        return result.scalar() or 0
