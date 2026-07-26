"""Router: /api/v1/users — Manajemen user. Hanya admin ke atas."""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.base import get_db
from backend.db.repositories.user_repo import UserRepository
from backend.db.models.user import User
from backend.core.security import hash_password, verify_password
from backend.api.schemas.user import UserCreate, UserUpdate, UserResponse
from backend.api.middleware.auth import get_current_user, require_role
from backend.services.audit import write_audit_log

router = APIRouter(tags=["users"])


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


class ResetPasswordRequest(BaseModel):
    new_password: str = Field(min_length=8)


@router.get("/me", response_model=UserResponse)
async def get_my_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me/password")
async def change_my_password(
    body: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not verify_password(body.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Password lama salah")

    repo = UserRepository(db)
    await repo.update_password(current_user.id, hash_password(body.new_password))
    await write_audit_log(
        db,
        action="user.password_change",
        user_id=current_user.id,
        target_type="user",
        target_id=str(current_user.id),
    )
    return {"message": "Password berhasil diubah"}


@router.get("", response_model=list[UserResponse])
async def list_users(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    repo = UserRepository(db)
    return await repo.get_active_users()


@router.post("", response_model=UserResponse, status_code=201)
async def create_user(
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    repo = UserRepository(db)
    existing = await repo.get_by_username(body.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username sudah dipakai")
    user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        email=body.email,
        full_name=body.full_name,
        role=body.role,
    )
    return await repo.create(user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404)
    updates = body.model_dump(exclude_none=True)
    if "password" in updates:
        updates["password_hash"] = hash_password(updates.pop("password"))
    for field, value in updates.items():
        setattr(user, field, value)
    await db.commit()
    await db.refresh(user)
    return user


@router.put("/{user_id}/reset-password")
async def admin_reset_password(
    user_id: str,
    body: ResetPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")

    await repo.update_password(user.id, hash_password(body.new_password))
    await write_audit_log(
        db,
        action="user.password_reset",
        user_id=current_user.id,
        target_type="user",
        target_id=str(user.id),
        detail={"username": user.username},
        ip_address=request.client.host if request.client else None,
    )
    return {"message": f"Password {user.username} berhasil direset"}
