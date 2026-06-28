"""
Pydantic schemas for configuration management API endpoints.
"""
from typing import Any
from pydantic import BaseModel, Field, field_validator


class MotionZoneConfig(BaseModel):
    """Motion zone configuration."""
    name: str
    coords: list[list[int]] | None = None
    sensitivity: float = 1.5


class CameraConfigCreate(BaseModel):
    """Schema for creating a new camera configuration."""
    id: str | None = None  # Auto-generate if empty
    name: str = Field(..., min_length=1, max_length=100)
    location: str | None = Field(None, max_length=100)
    ip_address: str = Field(..., description="Camera IP address")
    port: int = Field(554, ge=1, le=65535)
    username: str = Field("admin", max_length=50)
    password: str = Field(..., min_length=1, max_length=100)
    channel: int = Field(1, ge=1, le=16)
    rtsp_main_custom: str | None = Field(None, description="Custom RTSP URL override")
    rtsp_sub_custom: str | None = Field(None, description="Custom substream RTSP URL")
    storage_drive: str = Field(..., description="Storage drive assignment")
    motion_enabled: bool = False
    retention_days: int = Field(30, ge=1, le=365)
    motion_zones: list[MotionZoneConfig] | None = None
    
    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str | None) -> str | None:
        if v and not v.startswith("cam_"):
            raise ValueError("Camera ID must start with 'cam_'")
        return v


class CameraConfigUpdate(BaseModel):
    """Schema for updating camera configuration."""
    name: str | None = Field(None, min_length=1, max_length=100)
    location: str | None = Field(None, max_length=100)
    ip_address: str | None = None
    port: int | None = Field(None, ge=1, le=65535)
    username: str | None = Field(None, max_length=50)
    password: str | None = Field(None, min_length=1, max_length=100)
    channel: int | None = Field(None, ge=1, le=16)
    rtsp_main_custom: str | None = None
    rtsp_sub_custom: str | None = None
    storage_drive: str | None = None
    motion_enabled: bool | None = None
    retention_days: int | None = Field(None, ge=1, le=365)
    motion_zones: list[MotionZoneConfig] | None = None


class SystemConfigUpdate(BaseModel):
    """Schema for updating system configuration."""
    storage_threshold_pct: float | None = Field(None, ge=1, le=100)
    segment_duration_s: int | None = Field(None, ge=60, le=3600)
    reconnect_delay_s: int | None = Field(None, ge=1, le=300)
    hls_segment_duration_s: int | None = Field(None, ge=1, le=30)
    motion_frame_skip: int | None = Field(None, ge=1, le=10)
    motion_cooldown_s: int | None = Field(None, ge=1, le=3600)
    motion_threshold_pct: float | None = Field(None, ge=1, le=100)
    av1_crf: int | None = Field(None, ge=0, le=63)
    av1_preset: int | None = Field(None, ge=0, le=13)
    av1_schedule_start: str | None = Field(None, pattern=r"^\d{2}:\d{2}$")
    av1_schedule_stop: str | None = Field(None, pattern=r"^\d{2}:\d{2}$")
    av1_max_parallel: int | None = Field(None, ge=1, le=8)


class NotificationConfigUpdate(BaseModel):
    """Schema for updating notification configuration."""
    telegram_bot_token: str | None = Field(None, max_length=200)
    telegram_chat_id: str | None = Field(None, max_length=100)
    telegram_enabled: bool | None = None
    email_host: str | None = Field(None, max_length=200)
    email_port: int | None = Field(None, ge=1, le=65535)
    email_user: str | None = Field(None, max_length=100)
    email_password: str | None = Field(None, max_length=200)
    email_enabled: bool | None = None
    notify_on_motion: bool | None = None
    notify_on_camera_offline: bool | None = None
    notify_on_disk_warning: bool | None = None
    disk_warning_threshold_pct: float | None = Field(None, ge=1, le=100)


class DriveAssignment(BaseModel):
    """Storage drive camera assignment."""
    drive: str
    cameras: list[str]


class StorageConfigUpdate(BaseModel):
    """Schema for updating storage configuration."""
    drive_assignments: list[DriveAssignment]


class RTSPTestRequest(BaseModel):
    """Schema for RTSP connection test request."""
    rtsp_url: str = Field(..., min_length=1)
    timeout_s: int = Field(10, ge=1, le=60)


class RTSPTestResponse(BaseModel):
    """Schema for RTSP connection test response."""
    success: bool
    message: str
    codec: str | None = None
    resolution: str | None = None
    fps: float | None = None


class NotificationTestRequest(BaseModel):
    """Schema for notification test request."""
    telegram: bool = False
    email: bool = False
    test_message: str = Field("Test notification from NVR System", max_length=500)


class NotificationTestResponse(BaseModel):
    """Schema for notification test response."""
    success: bool
    message: str
    telegram_sent: bool = False
    email_sent: bool = False


class ConfigApplyResponse(BaseModel):
    """Schema for config apply response."""
    success: bool
    message: str
    restarted: list[str] = []
    started: list[str] = []
    stopped: list[str] = []
    errors: list[str] = []


class BackupInfo(BaseModel):
    """Schema for backup information."""
    filename: str
    created_at: str
    size_bytes: int


class BackupListResponse(BaseModel):
    """Schema for backup list response."""
    backups: list[BackupInfo]


class ConfigResponse(BaseModel):
    """Generic config response wrapper."""
    data: dict[str, Any]
