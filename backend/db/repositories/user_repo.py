"""Repository untuk operasi database terkait User."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.db.models.user import User
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
