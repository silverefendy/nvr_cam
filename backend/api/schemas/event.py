from datetime import datetime
from pydantic import BaseModel


class EventResponse(BaseModel):
    id: int
    camera_id: str
    zone_name: str | None
    started_at: datetime
    ended_at: datetime | None
    duration_s: int | None
    snapshot_url: str | None = None
    severity: int
    created_at: datetime

    class Config:
        from_attributes = True


class EventSummary(BaseModel):
    date: str
    total_events: int
    by_camera: dict[str, int]
    by_severity: dict[str, int]
