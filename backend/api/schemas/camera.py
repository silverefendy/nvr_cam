from datetime import datetime
from pydantic import BaseModel


class CameraBase(BaseModel):
    name: str
    location: str | None = None
    rtsp_main: str
    rtsp_sub: str | None = None
    storage_drive: str
    motion_enabled: bool = False
    retention_days: int = 30
    sort_order: int = 0
    config_json: dict | None = None


class CameraCreate(CameraBase):
    id: str  # "cam_01"


class CameraUpdate(BaseModel):
    name: str | None = None
    location: str | None = None
    rtsp_main: str | None = None
    rtsp_sub: str | None = None
    motion_enabled: bool | None = None
    retention_days: int | None = None
    sort_order: int | None = None
    config_json: dict | None = None
    is_active: bool | None = None


class CameraResponse(CameraBase):
    id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    # Runtime fields (tidak dari DB)
    status: str = "unknown"        # online | offline | unknown
    last_snapshot_url: str | None = None

    class Config:
        from_attributes = True
