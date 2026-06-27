"""
SQLAlchemy ORM Models — semua tabel database di sini.
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger, Boolean, DateTime, Float, ForeignKey,
    Integer, SmallInteger, String, Text, func
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.connection import Base


# ── Users ────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str]        = mapped_column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(100), unique=True)
    password_hash: Mapped[str]   = mapped_column(Text, nullable=False)
    role: Mapped[str]            = mapped_column(String(20), nullable=False, default="viewer")
    full_name: Mapped[Optional[str]] = mapped_column(String(100))
    is_active: Mapped[bool]      = mapped_column(Boolean, default=True)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ── Cameras ──────────────────────────────────────────────────
class Camera(Base):
    __tablename__ = "cameras"

    id: Mapped[str]              = mapped_column(String(20), primary_key=True)  # cam_01
    name: Mapped[str]            = mapped_column(String(100), nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(100))
    rtsp_main: Mapped[str]       = mapped_column(Text, nullable=False)
    rtsp_sub: Mapped[Optional[str]] = mapped_column(Text)
    storage_drive: Mapped[str]   = mapped_column(String(50), nullable=False)
    motion_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    retention_days: Mapped[int]  = mapped_column(Integer, default=30)
    segment_duration: Mapped[int] = mapped_column(Integer, default=3600)
    status: Mapped[str]          = mapped_column(String(20), default="offline")
    is_active: Mapped[bool]      = mapped_column(Boolean, default=True)
    config_json: Mapped[Optional[dict]] = mapped_column(JSONB)
    last_seen: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    recordings: Mapped[list["Recording"]] = relationship(back_populates="camera")
    motion_events: Mapped[list["MotionEvent"]] = relationship(back_populates="camera")


# ── Recordings ───────────────────────────────────────────────
class Recording(Base):
    __tablename__ = "recordings"

    id: Mapped[int]              = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    camera_id: Mapped[str]       = mapped_column(String(20), ForeignKey("cameras.id"), index=True)
    file_path: Mapped[str]       = mapped_column(Text, unique=True, nullable=False)
    file_size_mb: Mapped[Optional[float]] = mapped_column(Float)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    duration_s: Mapped[Optional[int]] = mapped_column(Integer)
    codec: Mapped[str]           = mapped_column(String(10), default="H265")
    is_protected: Mapped[bool]   = mapped_column(Boolean, default=False)
    is_encoded_av1: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    camera: Mapped["Camera"] = relationship(back_populates="recordings")
    motion_events: Mapped[list["MotionEvent"]] = relationship(back_populates="recording")


# ── Motion Events ────────────────────────────────────────────
class MotionEvent(Base):
    __tablename__ = "motion_events"

    id: Mapped[int]              = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    camera_id: Mapped[str]       = mapped_column(String(20), ForeignKey("cameras.id"), index=True)
    recording_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("recordings.id"))
    zone_name: Mapped[Optional[str]] = mapped_column(String(50))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    duration_s: Mapped[Optional[int]] = mapped_column(Integer)
    snapshot_path: Mapped[Optional[str]] = mapped_column(Text)
    video_offset_s: Mapped[Optional[int]] = mapped_column(Integer)
    severity: Mapped[int]        = mapped_column(SmallInteger, default=1)
    notified: Mapped[bool]       = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    camera: Mapped["Camera"] = relationship(back_populates="motion_events")
    recording: Mapped[Optional["Recording"]] = relationship(back_populates="motion_events")


# ── System Logs ──────────────────────────────────────────────
class SystemLog(Base):
    __tablename__ = "system_logs"

    id: Mapped[int]              = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    level: Mapped[str]           = mapped_column(String(10))        # INFO WARN ERROR
    service: Mapped[str]         = mapped_column(String(30))        # recorder motion api
    message: Mapped[str]         = mapped_column(Text)
    metadata: Mapped[Optional[dict]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


# ── Notification Log ─────────────────────────────────────────
class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id: Mapped[int]              = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    type: Mapped[str]            = mapped_column(String(30))
    channel: Mapped[str]         = mapped_column(String(20))
    status: Mapped[str]          = mapped_column(String(10))        # sent failed
    payload: Mapped[Optional[dict]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ── App Settings ─────────────────────────────────────────────
class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str]             = mapped_column(String(100), primary_key=True)
    value: Mapped[Optional[str]] = mapped_column(Text)
    description: Mapped[Optional[str]] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
