"""Repository untuk operasi database terkait User."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.db.models.user import User
from backend.core.security import get_password_hash
from .base_repo import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, db: AsyncSession):
        super().__init__(User, db)

    async def get_by_username(self, username: str) -> User | None:
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def get_active_users(self) -> list[User]:
        result = await self.db.execute(
            select(User).where(User.is_active == True).order_by(User.username)
        )
        return result.scalars().all()

    async def update_password(self, user_id: str, new_password: str) -> User:
        user = await self.get_by_id(user_id)
        if user:
            user.password_hash = get_password_hash(new_password)
            await self.db.commit()
            await self.db.refresh(user)
        return user

    async def update_last_login(self, user_id: str):
        from datetime import datetime, timezone
        user = await self.get_by_id(user_id)
        if user:
            user.last_login = datetime.now(timezone.utc)
            await self.db.commit()
