"""
FastAPI dependencies — auth, DB session, dll.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from core.constants import Role
from db.connection import get_db
from db.models import User
from db.repositories.camera_repo import CameraRepository
from db.repositories.recording_repo import RecordingRepository
from db.repositories.event_repo import EventRepository
from services.auth.jwt_handler import decode_token

security = HTTPBearer()
settings = get_settings()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token tidak valid")
    
    from sqlalchemy import select
    result = await db.execute(select(User).where(User.id == payload["sub"]))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User tidak ditemukan")
    return user


def require_role(*roles: str):
    """Decorator untuk require role tertentu."""
    async def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Akses ditolak")
        return current_user
    return checker


# ── Repository dependencies ───────────────────────────────────
def get_camera_repo(db: AsyncSession = Depends(get_db)) -> CameraRepository:
    return CameraRepository(db)

def get_recording_repo(db: AsyncSession = Depends(get_db)) -> RecordingRepository:
    return RecordingRepository(db)

def get_event_repo(db: AsyncSession = Depends(get_db)) -> EventRepository:
    return EventRepository(db)
