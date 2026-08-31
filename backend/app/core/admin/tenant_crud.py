from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Tuple

from app.core.crud.base import CRUDBase
from app.core.admin.models import Tenant
from app.core.admin.schemas import TenantCreate, TenantUpdate


class CRUDTenant(CRUDBase[Tenant, TenantCreate, TenantUpdate]):
    """CRUD для Tenant с использованием базового класса"""
    
    async def get_multi_active(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Tenant]:
        """Получить только активные tenants"""
        query = (
            select(Tenant)
            .where(Tenant.active == True)
            .offset(skip)
            .limit(limit)
            .order_by(Tenant.name)
        )
        result = await db.execute(query)
        return list(result.scalars().all())
    
    async def get_multi_paginated_active(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
    ) -> Tuple[List[Tenant], int]:
        """Получить активные tenants с пагинацией и поиском"""
        from sqlalchemy import func
        
        data_query = select(Tenant).where(Tenant.active == True)
        count_query = select(func.count(Tenant.id)).select_from(Tenant).where(Tenant.active == True)
        
        if search:
            filter_condition = Tenant.name.ilike(f"%{search}%")
            data_query = data_query.where(filter_condition)
            count_query = count_query.where(filter_condition)
        
        count_result = await db.execute(count_query)
        total: int = count_result.scalar_one()
        
        data_query = data_query.offset(skip).limit(limit).order_by(Tenant.name)
        data_result = await db.execute(data_query)
        items = list(data_result.scalars().all())
        
        return items, total


# ✅ Создаём экземпляр класса (именно это должно экспортироваться!)
tenant_crud = CRUDTenant(Tenant)