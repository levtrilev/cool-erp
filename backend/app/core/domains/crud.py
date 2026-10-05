import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.core.domains.models import DomainModel
from app.core.domains.schemas import DomainCreateSchema, DomainUpdateSchema
from app.core.crud.base import CRUDBase


class CRUDDomain(CRUDBase[DomainModel, DomainCreateSchema, DomainUpdateSchema]):
    """
    CRUD для доменов.
    
    ✅ Правило №31: Наследуемся от CRUDBase.
    Переопределяем только те методы, где нужна специфичная бизнес-логика:
    - create — проверка уникальности name
    - update — проверка уникальности name при изменении
    - remove — защита от удаления, если в домене есть doctypes
    
    НЕ переопределяем (используем базовые методы):
    - get — базовая реализация подходит
    - get_multi_paginated — базовая реализация подходит (поиск по name)
    """

    async def create(
        self,
        db: AsyncSession,
        obj_in: DomainCreateSchema,
        tenant_id: Optional[uuid.UUID] = None,
        user_is_superadmin: bool = False,
    ) -> DomainModel:
        """
        Создание домена с проверкой уникальности имени.
        
        Переопределено, т.к. нужна проверка уникальности name.
        """
        if not user_is_superadmin:
            raise HTTPException(status_code=403, detail="Только для суперадмина")

        # Проверка уникальности name
        stmt = select(self.model).where(self.model.name == obj_in.name)
        if (await db.execute(stmt)).scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail=f"Домен '{obj_in.name}' уже существует"
            )

        # Создаём объект
        db_obj = self.model(**obj_in.model_dump())
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        db_obj: DomainModel,
        obj_in: DomainUpdateSchema,
        tenant_id: Optional[uuid.UUID] = None,
        user_is_superadmin: bool = False,
    ) -> DomainModel:
        """
        Обновление домена с проверкой уникальности имени.
        
        Переопределено, т.к. нужна проверка уникальности name при изменении.
        """
        if not user_is_superadmin:
            raise HTTPException(status_code=403, detail="Только для суперадмина")

        # Проверка уникальности при изменении name
        update_data = obj_in.model_dump(exclude_unset=True)
        if "name" in update_data and update_data["name"] != db_obj.name:
            stmt_check = select(self.model).where(
                self.model.name == update_data["name"]
            )
            if (await db.execute(stmt_check)).scalar_one_or_none():
                raise HTTPException(
                    status_code=400,
                    detail=f"Домен '{update_data['name']}' уже существует"
                )

        # Обновляем поля
        for key, value in update_data.items():
            setattr(db_obj, key, value)

        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def remove(
        self,
        db: AsyncSession,
        id: uuid.UUID,
    ) -> Optional[DomainModel]:
        """
        Удаление домена с защитой от удаления, если есть doctypes.
        
        Переопределено, т.к. нужна проверка наличия связанных doctypes.
        """
        db_obj = await self.get(db, id=id)
        if not db_obj:
            return None

        # ✅ Защита: нельзя удалить домен, если в нём есть типы документов
        if len(db_obj.doctypes) > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Невозможно удалить домен: в нём содержится {len(db_obj.doctypes)} "
                       f"типов документов. Сначала удалите или перенесите их."
            )

        await db.delete(db_obj)
        await db.commit()
        return db_obj


# ✅ Экземпляр CRUD
crud_domain = CRUDDomain(DomainModel)