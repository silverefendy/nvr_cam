"""Router: /api/v1/users — Manajemen user. Hanya admin ke atas."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.base import get_db
from backend.db.repositories.user_repo import UserRepository
from backend.db.models.user import User
from backend.core.security import hash_password
from backend.api.schemas.user import UserCreate, UserUpdate, UserResponse
from backend.api.middleware.auth import require_role

router = APIRouter(tags=["users"])


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
