from typing import TypeVar

from pydantic import BaseModel
from sqlalchemy import and_, select

from app.core.errors import ConflictError
from app.db.session import Base
from app.repositories.lookupRepository import LookupRepository

ModelType = TypeVar("ModelType", bound=Base)  # type: ignore


class LookupService:
    def __init__(self, model: type[ModelType], repository: LookupRepository):
        self.model = model
        self.repo = repository

    async def get_all(
        self, skip: int = 0, limit: int = 20, is_active: bool | None = None
    ) -> list[ModelType]:
        return await self.repo.get_all(skip=skip, limit=limit, is_active=is_active)

    async def create(self, schema: BaseModel) -> ModelType:
        data = schema.model_dump()
        if hasattr(self.model, "code"):
            existing = await self.repo.db.execute(
                select(self.model).where(self.model.code == data["code"])
            )
            if existing.scalar_one_or_none():
                raise ConflictError(
                    code="Duplicate_Code",
                    message=f"A {self.model.__name__} with code '{data['code']}' already exists.",
                )
        return await self.repo.create(data)

    async def update(self, id: int, schema: BaseModel) -> ModelType:
        data = schema.model_dump(exclude_unset=True)
        if "code" in data and hasattr(self.model, "code"):
            existing = await self.repo.db.execute(
                select(self.model).where(
                    and_(self.model.code == data["code"], self.model.id != id)
                )
            )
            if existing.scalar_one_or_none():
                raise ConflictError(
                    code="Duplicate_Code",
                    message=f"A {self.model.__name__} with code '{data['code']}' already exists.",
                )
        return await self.repo.update(id, data)

    async def delete(self, id: int) -> None:
        await self.repo.delete(id)
