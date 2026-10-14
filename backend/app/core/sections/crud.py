import uuid
from typing import Any
from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.sections.models import SectionModel
from app.core.sections.schemas import SectionCreateSchema, SectionUpdateSchema


class SectionCRUD:
    """
    CRUD-операции для разделов (sections).
    Все методы учитывают tenant_id для изоляции данных между организациями.
    """

    def __init__(self, model: type[SectionModel]):
        self.model = model

    async def get(
        self, db: AsyncSession, id: uuid.UUID, tenant_id: uuid.UUID
    ) -> SectionModel | None:
        """Получить раздел по ID и tenant_id."""
        stmt = select(self.model).where(
            self.model.id == id,
            self.model.tenant_id == tenant_id,
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(
        self, db: AsyncSession, tenant_id: uuid.UUID, name: str
    ) -> SectionModel | None:
        """Получить раздел по имени и tenant_id (для проверки уникальности)."""
        stmt = select(self.model).where(
            self.model.tenant_id == tenant_id,
            self.model.name == name,
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self, db: AsyncSession, obj_in: SectionCreateSchema, tenant_id: uuid.UUID
    ) -> SectionModel:
        """
        Создать новый раздел.
        tenant_id берется из аргумента (обычно из сессии), а не из схемы,
        чтобы предотвратить подмену тенанта злоумышленником.
        """
        existing = await self.get_by_name(db, tenant_id, obj_in.name)
        if existing:
            raise HTTPException(
                status_code=400,
                detail="Раздел с таким названием уже существует в этой организации",
            )
        db_obj = self.model(
            name=obj_in.name,
            tenant_id=tenant_id,
        )
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        db_obj: SectionModel,
        obj_in: SectionUpdateSchema | dict[str, Any],
    ) -> SectionModel:
        """Обновить существующий раздел."""
        update_data = obj_in if isinstance(obj_in, dict) else obj_in.model_dump(exclude_unset=True)

        if "name" in update_data and update_data["name"] != db_obj.name:
            existing = await self.get_by_name(db, db_obj.tenant_id, update_data["name"])
            if existing and existing.id != db_obj.id:
                raise HTTPException(
                    status_code=400,
                    detail="Раздел с таким названием уже существует в этой организации",
                )

        for field, value in update_data.items():
            if value is not None:
                setattr(db_obj, field, value)

        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def delete(
        self, db: AsyncSession, id: uuid.UUID, tenant_id: uuid.UUID
    ) -> SectionModel | None:
        """Удалить раздел."""
        obj = await self.get(db, id, tenant_id)
        if not obj:
            return None
        await db.delete(obj)
        await db.flush()
        return obj

    async def get_multi(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
        user_is_superadmin: bool = False,
        target_tenant_id: uuid.UUID | None = None,  # ✅ НОВОЕ
    ) -> list[SectionModel]:
        # ✅ Приоритет: если передан target_tenant_id (для суперадмина), используем его
        effective_tenant = target_tenant_id if (user_is_superadmin and target_tenant_id) else tenant_id

        # ✅ Для справочника роли всегда фильтруем по предприятию
        stmt = select(self.model).where(self.model.tenant_id == effective_tenant)

        if search:
            stmt = stmt.where(self.model.name.ilike(f"%{search}%"))

        stmt = stmt.offset(skip).limit(limit).order_by(self.model.name)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_multi_paginated(
        self,
        db: AsyncSession,
        user_tenant_id: uuid.UUID,
        skip: int = 0,
        limit: int = 10,
        search: str | None = None,
        user_is_superadmin: bool = False,
        target_tenant_id: uuid.UUID | None = None,  # ✅ НОВОЕ
    ) -> tuple[list[SectionModel], int]:
        effective_tenant = target_tenant_id if (user_is_superadmin and target_tenant_id) else user_tenant_id

        count_stmt = (
            select(func.count())
            .select_from(self.model)
            .where(self.model.tenant_id == effective_tenant)
        )
        if search:
            count_stmt = count_stmt.where(self.model.name.ilike(f"%{search}%"))

        count_result = await db.execute(count_stmt)
        total = count_result.scalar_one()

        items = await self.get_multi(
            db, user_tenant_id, skip, limit, search, user_is_superadmin, target_tenant_id=target_tenant_id
        )
        return items, total

crud_section = SectionCRUD(SectionModel)


    # async def get_multi(
    #     self,
    #     db: AsyncSession,
    #     tenant_id: uuid.UUID,
    #     skip: int = 0,
    #     limit: int = 100,
    #     search: str | None = None,
    #     user_is_superadmin: bool = False,
    #     # ✅ НОВОЕ: опциональный target_tenant_id для суперадмина
    #     target_tenant_id: uuid.UUID | None = None,
    # ) -> list[SectionModel]:
    #     """
    #     Получить список разделов с опциональным поиском по имени.
        
    #     Если передан target_tenant_id и пользователь — суперадмин,
    #     фильтрация идёт по target_tenant_id (разделы другого предприятия).
    #     """
    #     # ✅ Определяем фактический tenant_id для фильтрации
    #     effective_tenant_id = target_tenant_id if (user_is_superadmin and target_tenant_id) else tenant_id

    #     if user_is_superadmin and not target_tenant_id:
    #         # Суперадмин без target_tenant_id видит ВСЕ разделы
    #         stmt = select(self.model)
    #     else:
    #         # Обычный админ ИЛИ суперадмин с target_tenant_id — фильтрация по tenant
    #         stmt = select(self.model).where(self.model.tenant_id == effective_tenant_id)

    #     if search:
    #         stmt = stmt.where(self.model.name.ilike(f"%{search}%"))

    #     stmt = stmt.offset(skip).limit(limit).order_by(self.model.name)
    #     result = await db.execute(stmt)
    #     return list(result.scalars().all())

    # async def get_multi_paginated(
    #     self,
    #     db: AsyncSession,
    #     user_tenant_id: uuid.UUID,
    #     skip: int = 0,
    #     limit: int = 10,
    #     search: str | None = None,
    #     user_is_superadmin: bool = False,
    #     # ✅ НОВОЕ: опциональный target_tenant_id для суперадмина
    #     target_tenant_id: uuid.UUID | None = None,
    # ) -> tuple[list[SectionModel], int]:
    #     """
    #     Получить пагинированный список разделов.
    #     Возвращает кортеж: (список объектов, общее количество).
    #     """
    #     # ✅ Определяем фактический tenant_id для фильтрации
    #     effective_tenant_id = target_tenant_id if (user_is_superadmin and target_tenant_id) else user_tenant_id

    #     if user_is_superadmin and not target_tenant_id:
    #         count_stmt = select(func.count()).select_from(self.model)
    #     else:
    #         count_stmt = (
    #             select(func.count())
    #             .select_from(self.model)
    #             .where(self.model.tenant_id == effective_tenant_id)
    #         )

    #     if search:
    #         count_stmt = count_stmt.where(self.model.name.ilike(f"%{search}%"))

    #     count_result = await db.execute(count_stmt)
    #     total = count_result.scalar_one()

    #     items = await self.get_multi(
    #         db,
    #         user_tenant_id,
    #         skip,
    #         limit,
    #         search,
    #         user_is_superadmin,
    #         target_tenant_id=target_tenant_id,
    #     )
    #     return items, total
