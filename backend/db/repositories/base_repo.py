"""
Base repository — semua repository extends kelas ini.
Pattern Repository: pisahkan logic DB dari logic bisnis.
"""
from typing import TypeVar, Generic, Type
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from backend.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType], db: AsyncSession):
        self.model = model
        self.db = db

    async def get_by_id(self, id: any) -> ModelType | None:
        return await self.db.get(self.model, id)

    async def get_all(self) -> list[ModelType]:
        result = await self.db.execute(select(self.model))
        return result.scalars().all()

    async def create(self, obj: ModelType) -> ModelType:
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete_by_id(self, id: any) -> bool:
        obj = await self.get_by_id(id)
        if obj:
            await self.db.delete(obj)
            return True
        return False
