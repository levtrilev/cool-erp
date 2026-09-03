# import uuid
# from typing import Any

# from fastapi import HTTPException
# from sqlalchemy import select, func
# from sqlalchemy.ext.asyncio import AsyncSession

# from app.core.crud.base import CRUDBase  # ← Импорт базового класса
# from app.core.sections.models import SectionModel
# from app.core.sections.schemas import SectionCreateSchema, SectionUpdateSchema


# class SectionCRUD(CRUDBase[SectionModel, SectionCreateSchema, SectionUpdateSchema]):
#     """
#     CRUD для разделов с учётом multi-tenancy.
#     Наследует общую логику от CRUDBase, но переопределяет методы,
#     чтобы добавить обязательную фильтрацию и проверку по tenant_id.
#     """

#     async def get(
#         self, db: AsyncSession, id: uuid.UUID, tenant_id: uuid.UUID
#     ) -> SectionModel | None:
#         """Получить раздел по ID с проверкой принадлежности к тенанту."""
#         stmt = select(self.model).where(
#             self.model.id == id,
#             self.model.tenant_id == tenant_id,
#         )
#         result = await db.execute(stmt)
#         return result.scalar_one_or_none()

#     async def get_by_name(
#         self, db: AsyncSession, tenant_id: uuid.UUID, name: str
#     ) -> SectionModel | None:
#         """Получить раздел по имени в рамках тенанта (для проверки уникальности)."""
#         stmt = select(self.model).where(
#             self.model.tenant_id == tenant_id,
#             self.model.name == name,
#         )
#         result = await db.execute(stmt)
#         return result.scalar_one_or_none()

#     async def get_multi(
#         self,
#         db: AsyncSession,
#         tenant_id: uuid.UUID,
#         skip: int = 0,
#         limit: int = 100,
#         search: str | None = None,
#     ) -> list[SectionModel]:
#         """Получить список разделов с фильтрацией по tenant_id и поиском."""
#         stmt = select(self.model).where(self.model.tenant_id == tenant_id)

#         if search:
#             stmt = stmt.where(self.model.name.ilike(f"%{search}%"))

#         stmt = stmt.offset(skip).limit(limit).order_by(self.model.name)
#         result = await db.execute(stmt)
#         return list(result.scalars().all())

#     async def get_multi_paginated(
#         self,
#         db: AsyncSession,
#         tenant_id: uuid.UUID,
#         skip: int = 0,
#         limit: int = 10,
#         search: str | None = None,
#     ) -> tuple[list[SectionModel], int]:
#         """Пагинированный список разделов."""
#         count_stmt = select(func.count()).select_from(self.model).where(
#             self.model.tenant_id == tenant_id
#         )
#         if search:
#             count_stmt = count_stmt.where(self.model.name.ilike(f"%{search}%"))

#         count_result = await db.execute(count_stmt)
#         total = count_result.scalar_one()

#         items = await self.get_multi(db, tenant_id, skip, limit, search)
#         return items, total

#     async def create(
#         self, db: AsyncSession, obj_in: SectionCreateSchema, tenant_id: uuid.UUID
#     ) -> SectionModel:
#         """Создать раздел с привязкой к тенанту и проверкой уникальности имени."""
#         existing = await self.get_by_name(db, tenant_id, obj_in.name)
#         if existing:
#             raise HTTPException(
#                 status_code=400,
#                 detail="Раздел с таким названием уже существует в этой организации",
#             )

#         # Создаём объект, явно указывая tenant_id из сессии (безопасность)
#         db_obj = self.model(
#             name=obj_in.name,
#             tenant_id=tenant_id,
#         )
#         db.add(db_obj)
#         await db.flush()
#         await db.refresh(db_obj)
#         return db_obj

#     async def update(
#         self,
#         db: AsyncSession,
#         db_obj: SectionModel,
#         obj_in: SectionUpdateSchema | dict[str, Any],
#     ) -> SectionModel:
#         """Обновить раздел с проверкой уникальности имени при его изменении."""
#         update_data = obj_in if isinstance(obj_in, dict) else obj_in.model_dump(exclude_unset=True)

#         if "name" in update_data and update_data["name"] != db_obj.name:
#             existing = await self.get_by_name(db, db_obj.tenant_id, update_data["name"])
#             if existing and existing.id != db_obj.id:
#                 raise HTTPException(
#                     status_code=400,
#                     detail="Раздел с таким названием уже существует в этой организации",
#                 )

#         # Вызываем базовый метод CRUDBase для применения изменений
#         # (если CRUDBase реализует общую логику обновления)
#         # Либо применяем вручную, если базовый метод не подходит:
#         for field, value in update_data.items():
#             if value is not None:
#                 setattr(db_obj, field, value)

#         await db.flush()
#         await db.refresh(db_obj)
#         return db_obj

#     async def delete(
#         self, db: AsyncSession, id: uuid.UUID, tenant_id: uuid.UUID
#     ) -> SectionModel | None:
#         """Удалить раздел с проверкой принадлежности к тенанту."""
#         obj = await self.get(db, id, tenant_id)
#         if not obj:
#             return None

#         # TODO: В будущем добавить проверку на связанные записи

#         await db.delete(obj)
#         await db.flush()
#         return obj


# # Экземпляр CRUD для использования в роутерах
# crud_section = SectionCRUD(SectionModel)