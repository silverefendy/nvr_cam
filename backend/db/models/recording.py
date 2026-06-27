"""Recording model — index metadata file rekaman. File fisik tetap di disk."""
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.db.base import Base


class Recording(Base):
    __tablename__ = "recordings"
    __table_args__ = (
        Index("idx_recordings_camera_time", "camera_id", "started_at"),
        Index("idx_recordings_time", "started_at"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    camera_id: Mapped[str] = mapped_column(String(20), ForeignKey("cameras.id"))
    file_path: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    file_size_mb: Mapped[float | None] = mapped_column(Float)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_s: Mapped[int | None] = mapped_column(Integer)
    codec: Mapped[str] = mapped_column(String(10), default="H265")
    is_protected: Mapped[bool] = mapped_column(Boolean, default=False)
    is_encoded_av1: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    camera: Mapped["Camera"] = relationship(back_populates="recordings")
    motion_events: Mapped[list["MotionEvent"]] = relationship(back_populates="recording")
