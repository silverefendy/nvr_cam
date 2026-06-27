"""
Pydantic schemas untuk request/response API.
Semua schema di satu file untuk kemudahan referensi.
"""
import uuid
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field, EmailStr


# ── Auth ─────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


# ── User ─────────────────────────────────────────────────────
class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    password: str = Field(min_length=8)
    role: str = "viewer"
    full_name: Optional[str] = None

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

class UserResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    username: str
    email: Optional[str]
    role: str
    full_name: Optional[str]
    is_active: bool
    last_login: Optional[datetime]
    created_at: datetime


# ── Camera ───────────────────────────────────────────────────
class CameraCreate(BaseModel):
    id: str = Field(pattern=r"^cam_\d+$")
    name: str
    location: Optional[str] = None
    rtsp_main: str
    rtsp_sub: Optional[str] = None
    storage_drive: str
    motion_enabled: bool = False
    retention_days: int = 30
    segment_duration: int = 3600

class CameraUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    rtsp_main: Optional[str] = None
    rtsp_sub: Optional[str] = None
    storage_drive: Optional[str] = None
    motion_enabled: Optional[bool] = None
    retention_days: Optional[int] = None
    is_active: Optional[bool] = None

class CameraResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: str
    name: str
    location: Optional[str]
    storage_drive: str
    motion_enabled: bool
    retention_days: int
    status: str
    is_active: bool
    last_seen: Optional[datetime]


# ── Recording ────────────────────────────────────────────────
class RecordingResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    camera_id: str
    file_path: str
    file_size_mb: Optional[float]
    started_at: datetime
    ended_at: Optional[datetime]
    duration_s: Optional[int]
    codec: str
    is_protected: bool
    is_encoded_av1: bool


# ── Motion Event ─────────────────────────────────────────────
class MotionEventResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    camera_id: str
    zone_name: Optional[str]
    started_at: datetime
    ended_at: Optional[datetime]
    duration_s: Optional[int]
    snapshot_path: Optional[str]
    video_offset_s: Optional[int]
    severity: int
    notified: bool


# ── Storage ──────────────────────────────────────────────────
class DriveStatus(BaseModel):
    mount: str
    label: str
    total_gb: float
    used_gb: float
    free_gb: float
    free_pct: float
    cameras: list[str]


# ── System ───────────────────────────────────────────────────
class SystemHealth(BaseModel):
    cpu_pct: float
    ram_pct: float
    ram_used_gb: float
    ram_total_gb: float
    cameras_online: int
    cameras_offline: int
    uptime_hours: float


# ── Generic ──────────────────────────────────────────────────
class MessageResponse(BaseModel):
    message: str

class PaginatedResponse(BaseModel):
    total: int
    limit: int
    offset: int
    data: list[Any]
