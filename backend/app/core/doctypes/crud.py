import uuid
from typing import Optional, Tuple, List

from sqlalchemy import select, delete, insert, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.core.crud.base import CRUDBase
from app.core.doctypes.models import DoctypeModel, doctype_tenants
from app.core.doctypes.schemas import (
    DoctypeCreateSchema,
    DoctypeUpdateSchema,
)


class CRUDDoctype(CRUDBase[DoctypeModel, DoctypeCreateSchema, DoctypeUpdateSchema]):
    """
    CRUD для типов документов.
    
    ✅ Правило №31: Наследуемся от CRUDBase.
    Переопределяем только те методы, где нужна специфичная бизнес-логика:
    - create — синхронизация M2M tenant_ids (Правило №30)
    - update — синхронизация M2M tenant_ids + проверка уникальности doctype
    - get_multi_paginated — поиск по двум полям + фильтрация через M2M таблицу
    
    НЕ переопределяем (используем базовые методы):
    - get — базовая реализация подходит
    - remove — базовая реализация подходит (каскадное удаление M2M настроено в модели)
    """

    async def create(
        self,
        db: AsyncSession,
        obj_in: DoctypeCreateSchema,
        tenant_id: Optional[uuid.UUID] = None,
        user_is_superadmin: bool = False,
    ) -> DoctypeModel:
        """
        Создание типа документа с синхронизацией тенантов.
        
        Переопределено, т.к. нужна синхронизация M2M связи tenant_ids.
        """
        if not user_is_superadmin:
            raise HTTPException(status_code=403, detail="Только для суперадмина")

        # Проверка уникальности doctype
        stmt = select(self.model).where(self.model.doctype == obj_in.doctype)
        if (await db.execute(stmt)).scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail=f"Тип документа '{obj_in.doctype}' уже существует"
            )

        # Создаём объект без tenant_ids (это не колонка, а M2M связь)
        db_obj = self.model(**obj_in.model_dump(exclude={'tenant_ids'}))
        db.add(db_obj)
        await db.flush()  # Получаем db_obj.id

        # ✅ Синхронизация M2M связи с тенантами (Правило №30)
        if obj_in.tenant_ids:
            await db.execute(
                insert(doctype_tenants),
                [{"doctype_id": db_obj.id, "tenant_id": tid} for tid in obj_in.tenant_ids]
            )

        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        db_obj: DoctypeModel,
        obj_in: DoctypeUpdateSchema,
        tenant_id: Optional[uuid.UUID] = None,
        user_is_superadmin: bool = False,
    ) -> DoctypeModel:
        """
        Обновление типа документа с синхронизацией тенантов.
        
        Переопределено, т.к. нужна синхронизация M2M связи tenant_ids + 
        проверка уникальности doctype.
        """
        if not user_is_superadmin:
            raise HTTPException(status_code=403, detail="Только для суперадмина")

        item_id = db_obj.id

        # Проверка уникальности при изменении doctype
        update_data = obj_in.model_dump(exclude_unset=True, exclude={'tenant_ids'})
        if "doctype" in update_data and update_data["doctype"] != db_obj.doctype:
            stmt_check = select(self.model).where(
                self.model.doctype == update_data["doctype"]
            )
            if (await db.execute(stmt_check)).scalar_one_or_none():
                raise HTTPException(
                    status_code=400,
                    detail=f"Тип документа '{update_data['doctype']}' уже существует"
                )

        # Обновляем обычные поля
        for key, value in update_data.items():
            setattr(db_obj, key, value)

        # ✅ Полная перезапись M2M связи с тенантами (если передана)
        if obj_in.tenant_ids is not None:
            await db.execute(
                delete(doctype_tenants).where(doctype_tenants.c.doctype_id == item_id)
            )
            if obj_in.tenant_ids:
                await db.execute(
                    insert(doctype_tenants),
                    [{"doctype_id": item_id, "tenant_id": tid} for tid in obj_in.tenant_ids]
                )

        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def get_multi_paginated(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        search_field: str = "doctype_name",  # Не используется, но сохраняем для совместимости
        user_is_superadmin: bool = False,
    ) -> Tuple[List[DoctypeModel], int]:
        """
        Получение списка типов документов с пагинацией и фильтрацией.
        
        Переопределено, т.к.:
        1. Нужен поиск по двум полям: doctype И doctype_name
        2. Фильтрация по tenant_id идёт через M2M таблицу doctype_tenants
        """
        stmt = select(self.model)
        count_stmt = select(func.count()).select_from(self.model)

        # ✅ Правило №26: Обычные пользователи видят только свои тенанты
        # Фильтрация через M2M таблицу
        if not user_is_superadmin:
            stmt = stmt.join(doctype_tenants).where(
                doctype_tenants.c.tenant_id == tenant_id
            )
            count_stmt = count_stmt.join(doctype_tenants).where(
                doctype_tenants.c.tenant_id == tenant_id
            )

        # ✅ Поиск по двум полям: doctype и doctype_name
        if search:
            search_filter = (
                self.model.doctype.ilike(f"%{search}%")
                | self.model.doctype_name.ilike(f"%{search}%")
            )
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)

        # Получаем общее количество
        total: int = (await db.execute(count_stmt)).scalar_one()

        # Получаем данные с пагинацией
        stmt = stmt.offset(skip).limit(limit).order_by(self.model.doctype_name)
        items = list((await db.execute(stmt)).scalars().all())

        # ✅ Правило №33: НИЧЕГО не присваиваем в @property!
        # tenant_ids и domain_name автоматически вычисляются при model_validate()
        
        return items, total


# ✅ Экземпляр CRUD
crud_doctype = CRUDDoctype(DoctypeModel)