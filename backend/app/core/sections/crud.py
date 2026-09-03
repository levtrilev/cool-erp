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
            self.model.tenant_id == tenant_id
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(
        self, db: AsyncSession, tenant_id: uuid.UUID, name: str
    ) -> SectionModel | None:
        """Получить раздел по имени и tenant_id (для проверки уникальности)."""
        stmt = select(self.model).where(
            self.model.tenant_id == tenant_id,
            self.model.name == name
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
    ) -> list[SectionModel]:
        """Получить список разделов с опциональным поиском по имени."""
        stmt = select(self.model).where(self.model.tenant_id == tenant_id)
        
        if search:
            # Регистронезависимый поиск по подстроке
            stmt = stmt.where(self.model.name.ilike(f"%{search}%"))
            
        stmt = stmt.offset(skip).limit(limit).order_by(self.model.name)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_multi_paginated(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        skip: int = 0,
        limit: int = 10,
        search: str | None = None,
    ) -> tuple[list[SectionModel], int]:
        """
        Получить пагинированный список разделов.
        Возвращает кортеж: (список объектов, общее количество).
        """
        # 1. Подсчет общего количества записей
        count_stmt = select(func.count()).select_from(self.model).where(
            self.model.tenant_id == tenant_id
        )
        if search:
            count_stmt = count_stmt.where(self.model.name.ilike(f"%{search}%"))
            
        count_result = await db.execute(count_stmt)
        total = count_result.scalar_one()

        # 2. Получение самих записей
        items = await self.get_multi(db, tenant_id, skip, limit, search)
        
        return items, total

    async def create(
        self, db: AsyncSession, obj_in: SectionCreateSchema, tenant_id: uuid.UUID
    ) -> SectionModel:
        """
        Создать новый раздел.
        tenant_id берется из аргумента (обычно из сессии), а не из схемы, 
        чтобы предотвратить подмену тенанта злоумышленником.
        """
        # Проверка уникальности имени в рамках тенанта
        existing = await self.get_by_name(db, tenant_id, obj_in.name)
        if existing:
            raise HTTPException(
                status_code=400, 
                detail="Раздел с таким названием уже существует в этой организации"
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
        
        # Если меняется имя, проверяем уникальность
        if "name" in update_data and update_data["name"] != db_obj.name:
            existing = await self.get_by_name(db, db_obj.tenant_id, update_data["name"])
            # Если нашли другой объект с таким именем
            if existing and existing.id != db_obj.id:
                raise HTTPException(
                    status_code=400, 
                    detail="Раздел с таким названием уже существует в этой организации"
                )

        for field, value in update_data.items():
            # Используем 'is not None', чтобы корректно обрабатывать False, 0, ""
            if value is not None:
                setattr(db_obj, field, value)
                
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def delete(
        self, db: AsyncSession, id: uuid.UUID, tenant_id: uuid.UUID
    ) -> SectionModel | None:
        """
        Удалить раздел.
        Использует get() для проверки принадлежности к tenant_id (безопасность).
        """
        obj = await self.get(db, id, tenant_id)
        if not obj:
            return None
            
        # TODO: В будущем добавить проверку на связанные записи (если появятся),
        # иначе бросать HTTPException(400, detail="Нельзя удалить раздел, так как он используется в...")
        
        await db.delete(obj)
        await db.flush()
        return obj


# Экземпляр CRUD для использования в роутерах
crud_section = SectionCRUD(SectionModel)