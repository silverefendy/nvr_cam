"""Camera model — registry semua kamera. Detail konfigurasi di config_json."""
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, Integer, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.db.base import Base


class Camera(Base):
    __tablename__ = "cameras"
    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    location: Mapped[str | None] = mapped_column(String(100))
    rtsp_main: Mapped[str] = mapped_column(String(500), nullable=False)
    rtsp_sub: Mapped[str | None] = mapped_column(String(500))
    storage_drive: Mapped[str] = mapped_column(String(50), nullable=False)
    motion_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    retention_days: Mapped[int] = mapped_column(Integer, default=30)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    config_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    recordings: Mapped[list["Recording"]] = relationship(back_populates="camera", lazy="dynamic")
    motion_events: Mapped[list["MotionEvent"]] = relationship(back_populates="camera", lazy="dynamic")
