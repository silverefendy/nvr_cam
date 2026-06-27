"""
Router: /api/v1/auth
Endpoint: login, refresh token, logout, me
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from backend.db.base import get_db
from backend.db.repositories.user_repo import UserRepository
from backend.core.security import verify_password, create_access_token, create_refresh_token
from backend.api.schemas.auth import LoginRequest, TokenResponse
from backend.api.schemas.user import UserResponse
from backend.api.middleware.auth import get_current_user
from backend.db.models.user import User

router = APIRouter(tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login dan dapatkan JWT token."""
    repo = UserRepository(db)
    user = await repo.get_by_username(body.username)
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Username atau password salah")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Akun tidak aktif")

    # Update last login
    user.last_login = datetime.now(timezone.utc)
    await db.commit()

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        role=user.role,
        username=user.username,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Ambil data user yang sedang login."""
    return current_user
