from typing import Any, TypeVar

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.db.session import Base

ModelType = TypeVar("ModelType", bound=Base)  # type: ignore


class LookupRepository:
    def __init__(self, model: type[ModelType], db_session: AsyncSession):
        self.model = model
        self.db = db_session

    async def get_all(
        self, skip: int = 0, limit: int = 100, is_active: bool | None = None
    ) -> list[ModelType]:
        query = select(self.model)
        if is_active is not None:
            query = query.where(self.model.is_active == is_active)
        query = query.offset(skip).limit(limit).order_by(self.model.id)
        result = await self.db.execute(query)
        return list(result.scalars().all())  # type: ignore

    async def get_by_id(self, id: int) -> ModelType | None:
        result = await self.db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def create(self, data: dict[str, Any]) -> ModelType:
        db_obj = self.model(**data)
        self.db.add(db_obj)
        await self.db.commit()
        await self.db.refresh(db_obj)
        return db_obj

    async def update(self, id: int, data: dict[str, Any]) -> ModelType:
        db_obj = await self.get_by_id(id)
        if not db_obj:
            raise NotFoundError(
                code=f"{self.model.__name__}_Not_Found",
                message=f"{self.model.__name__} with id {id} not found",
            )
        for field, value in data.items():
            setattr(db_obj, field, value)
        await self.db.commit()
        await self.db.refresh(db_obj)
        return db_obj

    async def delete(self, id: int) -> None:
        db_obj = await self.get_by_id(id)
        if not db_obj:
            raise NotFoundError(
                code=f"{self.model.__name__}_Not_Found",
                message=f"{self.model.__name__} with id {id} not found",
            )
        try:
            await self.db.delete(db_obj)
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise ConflictError(
                code="Dependency_Exists",
                message=f"Cannot delete {self.model.__name__} because it is currently being used by other records.",
            )
