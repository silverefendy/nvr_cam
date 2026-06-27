"""SystemLog model — semua log kejadian sistem tersimpan di DB."""
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column
from backend.db.base import Base


class SystemLog(Base):
    __tablename__ = "system_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    level: Mapped[str] = mapped_column(String(10))
    service: Mapped[str] = mapped_column(String(30))
    message: Mapped[str] = mapped_column(String(1000))
    metadata: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
