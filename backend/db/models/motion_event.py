"""MotionEvent model — setiap kejadian motion yang terdeteksi OpenCV."""
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, SmallInteger, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.db.base import Base


class MotionEvent(Base):
    __tablename__ = "motion_events"
    __table_args__ = (Index("idx_motion_camera_time", "camera_id", "started_at"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    camera_id: Mapped[str] = mapped_column(String(20), ForeignKey("cameras.id"))
    recording_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("recordings.id"))
    zone_name: Mapped[str | None] = mapped_column(String(50))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_s: Mapped[int | None] = mapped_column(Integer)
    snapshot_path: Mapped[str | None] = mapped_column(String(500))
    video_offset_s: Mapped[int | None] = mapped_column(Integer)
    severity: Mapped[int] = mapped_column(SmallInteger, default=1)
    notified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    camera: Mapped["Camera"] = relationship(back_populates="motion_events")
    recording: Mapped["Recording"] = relationship(back_populates="motion_events")
