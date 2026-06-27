"""Router: /api/v1/events — Motion detection events."""
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.base import get_db
from backend.db.repositories.event_repo import EventRepository
from backend.api.schemas.event import EventResponse
from backend.api.middleware.auth import get_current_user
from backend.db.models.user import User

router = APIRouter(tags=["events"])


@router.get("", response_model=list[EventResponse])
async def list_events(
    camera_id: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    severity: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    repo = EventRepository(db)
    if camera_id and date_from and date_to:
        return await repo.get_by_camera_and_date(camera_id, date_from, date_to)
    return await repo.get_all()
