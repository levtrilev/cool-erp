# backend/app/core/tenant/crud.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, or_, func
from app.core.tenant.models import TenantModel
from app.core.users.models import UserModel
from typing import Optional
import uuid


class CRUDTenant:
    """CRUD операции для работы с организациями (Tenants)"""

    async def create(
        self, 
        db: AsyncSession, 
        name: str, 
        description: Optional[str] = None,
        active: bool = True
    ) -> TenantModel:
        """Создание новой организации"""
        new_tenant = TenantModel(name=name, active=active)
        if description is not None:
            new_tenant.description = description
        db.add(new_tenant)
        await db.flush()  # Flush, чтобы получить ID до коммита
        return new_tenant

    async def get(self, db: AsyncSession, id: uuid.UUID) -> Optional[TenantModel]:
        """Получение организации по ID"""
        result = await db.execute(select(TenantModel).where(TenantModel.id == id))
        return result.scalar_one_or_none()

    async def get_by_name(self, db: AsyncSession, name: str) -> Optional[TenantModel]:
        """Получение организации по названию"""
        result = await db.execute(select(TenantModel).where(TenantModel.name == name))
        return result.scalar_one_or_none()

    async def get_multi(
        self, 
        db: AsyncSession, 
        skip: int = 0, 
        limit: int = 100, 
        search: Optional[str] = None,
        active_only: bool = False
    ) -> list[TenantModel]:
        """Получение списка организаций с пагинацией, поиском и фильтром по активности"""
        query = select(TenantModel)
        
        # Фильтр по активности
        if active_only:
            query = query.where(TenantModel.active == True)
        
        # Поиск по имени и описанию
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    TenantModel.name.ilike(search_pattern),
                    TenantModel.description.ilike(search_pattern)
                )
            )
            
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        
        # ✅ ЯВНАЯ ТИПИЗАЦИЯ для Pylance/Pyright
        items: list[TenantModel] = list(result.scalars().all())
        return items

    async def get_multi_paginated(
        self, 
        db: AsyncSession, 
        skip: int = 0, 
        limit: int = 100, 
        search: Optional[str] = None,
        active_only: bool = False
    ) -> tuple[list[TenantModel], int]:
        """
        Получение списка организаций с пагинацией, поиском, фильтром по активности и общим количеством.
        Возвращает кортеж: (список_объектов, общее_количество)
        """
        query = select(TenantModel)
        count_query = select(func.count(TenantModel.id))
        
        # Базовые фильтры
        filters = []
        
        if active_only:
            filters.append(TenantModel.active == True) # pyright: ignore[reportUnknownMemberType]
        
        if search:
            search_pattern = f"%{search}%"
            filters.append( # pyright: ignore[reportUnknownMemberType]
                or_(
                    TenantModel.name.ilike(search_pattern),
                    TenantModel.description.ilike(search_pattern)
                )
            )
        
        # Применяем фильтры
        if filters:
            query = query.where(*filters) # pyright: ignore[reportUnknownArgumentType]
            count_query = count_query.where(*filters) # pyright: ignore[reportUnknownArgumentType]
            
        # Получаем общее количество
        total_result = await db.execute(count_query)
        total = total_result.scalar_one()
        
        # Получаем сами записи
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        
        # ✅ ЯВНАЯ ТИПИЗАЦИЯ для Pylance/Pyright
        items: list[TenantModel] = list(result.scalars().all())
        
        return items, total

    async def update(
        self, 
        db: AsyncSession, 
        db_obj: TenantModel, 
        name: Optional[str] = None, 
        description: Optional[str] = None,
        active: Optional[bool] = None
    ) -> TenantModel:
        """Обновление данных организации"""
        if name is not None:
            db_obj.name = name
        if description is not None:
            db_obj.description = description
        if active is not None:
            db_obj.active = active
        db.add(db_obj)
        await db.flush()
        return db_obj

    async def delete(self, db: AsyncSession, id: uuid.UUID) -> Optional[TenantModel]:
        """
        Удаление организации.
        Проверяет, нет ли связанных пользователей. Если есть - возвращает None и не удаляет.
        """
        # Сначала проверяем, есть ли пользователи в этой организации
        result = await db.execute(
            select(UserModel).where(UserModel.tenant_id == id).limit(1)
        )
        has_users = result.scalar_one_or_none()
        
        if has_users:
            # Если есть пользователи, не удаляем
            return None
        
        # Если пользователей нет, удаляем организацию
        result = await db.execute(
            select(TenantModel).where(TenantModel.id == id)
        )
        
        # ✅ ЯВНАЯ ТИПИЗАЦИЯ для Pylance/Pyright
        db_obj: Optional[TenantModel] = result.scalar_one_or_none()
        
        if db_obj:
            await db.execute(delete(TenantModel).where(TenantModel.id == id))
            await db.flush()
        
        return db_obj


# Экземпляр для использования в роутерах
crud_tenant = CRUDTenant()