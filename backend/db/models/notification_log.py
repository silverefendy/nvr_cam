"""NotificationLog model — riwayat notifikasi Telegram dan email."""
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column
from backend.db.base import Base


class NotificationLog(Base):
    __tablename__ = "notification_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String(30))
    channel: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(10))
    payload: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
