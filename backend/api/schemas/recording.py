from datetime import datetime
from pydantic import BaseModel


class RecordingResponse(BaseModel):
    id: int
    camera_id: str
    file_path: str
    file_size_mb: float | None
    started_at: datetime
    ended_at: datetime | None
    duration_s: int | None
    codec: str
    is_protected: bool
    is_encoded_av1: bool
    play_url: str | None = None   # diisi oleh router

    class Config:
        from_attributes = True
