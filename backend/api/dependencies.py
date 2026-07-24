"""
FastAPI dependencies — auth, DB session, dll.
Semua fungsi auth di sini delegasi ke middleware/auth.py agar konsisten.
"""
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.middleware.auth import get_current_user, require_role
from backend.db.base import get_db
from backend.db.models.user import User
from backend.db.repositories.camera_repo import CameraRepository
from backend.db.repositories.recording_repo import RecordingRepository
from backend.db.repositories.event_repo import EventRepository


async def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Dependency untuk user dengan role admin atau super_admin."""
    from backend.api.middleware.auth import ROLE_HIERARCHY
    user_level = ROLE_HIERARCHY.get(current_user.role, 0)
    admin_level = ROLE_HIERARCHY.get("admin", 4)
    if user_level < admin_level:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses ditolak - minimal role admin"
        )
    return current_user


# ── Repository dependencies ───────────────────────────────────
def get_camera_repo(db: AsyncSession = Depends(get_db)) -> CameraRepository:
    return CameraRepository(db)

def get_recording_repo(db: AsyncSession = Depends(get_db)) -> RecordingRepository:
    return RecordingRepository(db)

def get_event_repo(db: AsyncSession = Depends(get_db)) -> EventRepository:
    return EventRepository(db)
