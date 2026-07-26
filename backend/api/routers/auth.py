"""
Router: /api/v1/auth
Endpoint: login, refresh token, logout, me
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from backend.db.base import get_db
from backend.db.repositories.user_repo import UserRepository
from backend.core.security import verify_password, create_access_token, create_refresh_token
from backend.api.schemas.auth import LoginRequest, TokenResponse
from backend.api.schemas.user import UserResponse
from backend.api.middleware.auth import get_current_user
from backend.db.models.user import User
from backend.services.audit import write_audit_log

router = APIRouter(tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Login dan dapatkan JWT token."""
    repo = UserRepository(db)
    user = await repo.get_by_username(body.username)
    if not user or not verify_password(body.password, user.password_hash):
        await write_audit_log(
            db,
            action="auth.login_failed",
            target_type="user",
            target_id=body.username,
            detail={"reason": "invalid_credentials"},
            ip_address=request.client.host if request.client else None,
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Username atau password salah")
    if not user.is_active:
        await write_audit_log(
            db,
            action="auth.login_failed",
            user_id=user.id,
            target_type="user",
            target_id=str(user.id),
            detail={"reason": "inactive"},
            ip_address=request.client.host if request.client else None,
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Akun tidak aktif")

    # Update last login
    user.last_login = datetime.now(timezone.utc)
    await db.commit()
    await write_audit_log(
        db,
        action="auth.login_success",
        user_id=user.id,
        target_type="user",
        target_id=str(user.id),
        ip_address=request.client.host if request.client else None,
    )

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
