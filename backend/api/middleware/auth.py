"""
Auth dependency — dipakai di semua router yang butuh login.
Penggunaan: tambahkan `current_user: User = Depends(require_auth)` di endpoint.
"""
import uuid
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
import jwt

from backend.core.config import settings
from backend.core.exceptions import AuthorizationError
from backend.db.base import get_db
from backend.db.repositories.user_repo import UserRepository
from backend.db.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

ROLE_HIERARCHY = {
    "super_admin": 5,
    "admin": 4,
    "operator": 3,
    "viewer": 2,
    "security": 1,
}


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        user_id_str: str = payload.get("sub")
        if not user_id_str:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        # Cast string UUID ke uuid.UUID agar cocok dengan tipe kolom PostgreSQL
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user ID in token")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return user


def require_role(minimum_role: str):
    """Factory: buat dependency yang require role minimum tertentu."""
    async def dependency(current_user: User = Depends(get_current_user)) -> User:
        user_level = ROLE_HIERARCHY.get(current_user.role, 0)
        required_level = ROLE_HIERARCHY.get(minimum_role, 99)
        if user_level < required_level:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return current_user
    return dependency


# Shortcut dependencies
require_auth     = Depends(get_current_user)
require_admin    = Depends(require_role("admin"))
require_operator = Depends(require_role("operator"))


async def get_current_super_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency: super_admin only."""
    if current_user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses ditolak - minimal role super_admin"
        )
    return current_user


async def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Dependency: admin + super_admin."""
    user_level = ROLE_HIERARCHY.get(current_user.role, 0)
    admin_level = ROLE_HIERARCHY.get("admin", 4)
    if user_level < admin_level:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses ditolak - minimal role admin"
        )
    return current_user


async def get_current_operator_user(current_user: User = Depends(get_current_user)) -> User:
    """Dependency: operator + admin + super_admin."""
    user_level = ROLE_HIERARCHY.get(current_user.role, 0)
    operator_level = ROLE_HIERARCHY.get("operator", 3)
    if user_level < operator_level:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses ditolak - minimal role operator"
        )
    return current_user


def has_permission(user: User, permission: str) -> bool:
    """Helper: cek permission berdasarkan matrix role."""
    role = user.role
    if role == "super_admin":
        return True

    admin_perms = {
        "live_view", "playback", "download_recording", "delete_recording", "snapshot",
        "add_camera", "edit_camera", "delete_camera", "restart_stream",
        "manage_users", "reset_password", "system_settings", "storage_settings",
        "backup_restore", "view_audit_logs", "view_storage_diagnostics", "manual_cleanup"
    }
    operator_perms = {
        "live_view", "playback", "download_recording", "snapshot", "restart_stream"
    }
    viewer_perms = {
        "live_view", "playback", "snapshot"
    }

    if role == "admin":
        return permission in admin_perms
    elif role == "operator":
        return permission in operator_perms
    elif role == "viewer":
        return permission in viewer_perms
    return False


async def get_current_user_flexible(
    request: Request,
    token_query: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Dependency khusus untuk endpoint video streaming.

    HTML5 <video src="..."> tidak bisa kirim Authorization header otomatis.
    Dependency ini cek header Authorization dulu, lalu fallback ke query
    param ?token=... jika header tidak ada.

    Urutan prioritas:
      1. Header: Authorization: Bearer <token>
      2. Query param: ?token=<token>
    """
    # Ambil token dari header dulu
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    else:
        token = token_query or request.query_params.get("token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token tidak ditemukan — pastikan sudah login",
        )

    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        user_id_str: str = payload.get("sub")
        if not user_id_str:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user ID in token")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return user
