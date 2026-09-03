# backend/app/core/tenant/router.py
from typing import Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.tenants.schemas import (
    TenantCreateSchema,
    TenantUpdateSchema,
    TenantResponseSchema,
)
from app.core.tenants.crud import crud_tenant
from app.core.schemas import PaginatedResponse

# Создаем роутер для управления организациями
router = APIRouter(prefix="/tenants", tags=["Tenants"])


# ==========================================
# ПОЛУЧЕНИЕ СПИСКА ОРГАНИЗАЦИЙ
# ==========================================
@router.get("/", response_model=PaginatedResponse[TenantResponseSchema])
async def read_tenants(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    active_only: bool = False,  # <-- ДОБАВЛЕНО: фильтр по активности
    db: AsyncSession = Depends(get_db),
):
    """Получение списка организаций с пагинацией, поиском и фильтром по активности"""
    items, total = await crud_tenant.get_multi_paginated(
        db, skip=skip, limit=limit, search=search, active_only=active_only
    )
    return PaginatedResponse[TenantResponseSchema](
        items=[TenantResponseSchema.model_validate(item) for item in items],
        total=total,
        page=(skip // limit) + 1,
        size=limit
    )


# ==========================================
# ПОЛУЧЕНИЕ ОДНОЙ ОРГАНИЗАЦИИ
# ==========================================
@router.get("/{tenant_id}", response_model=TenantResponseSchema)
async def read_tenant(tenant_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Получение одной организации по UUID"""
    db_tenant = await crud_tenant.get(db, id=tenant_id)
    if db_tenant is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return TenantResponseSchema.model_validate(db_tenant)


# ==========================================
# СОЗДАНИЕ ОРГАНИЗАЦИИ
# ==========================================
@router.post("/", status_code=status.HTTP_201_CREATED, response_model=TenantResponseSchema)
async def create_tenant(
    tenant_in: TenantCreateSchema,
    db: AsyncSession = Depends(get_db),
):
    """Создание новой организации"""
    existing_tenant = await crud_tenant.get_by_name(db, name=tenant_in.name)
    if existing_tenant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Организация с таким названием уже существует",
        )
    
    try:
        new_tenant = await crud_tenant.create(
            db,
            name=tenant_in.name,
            description=tenant_in.description,
            active=tenant_in.active  # <-- ПЕРЕДАЕМ active
        )
        await db.commit()
        await db.refresh(new_tenant)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при создании организации: {str(e)}",
        )
    
    return TenantResponseSchema.model_validate(new_tenant)


# ==========================================
# ОБНОВЛЕНИЕ ОРГАНИЗАЦИИ
# ==========================================
@router.put("/{tenant_id}", response_model=TenantResponseSchema)
async def update_tenant(
    tenant_id: uuid.UUID,
    tenant_changes: TenantUpdateSchema,
    db: AsyncSession = Depends(get_db),
):
    """Обновление данных организации"""
    db_tenant = await crud_tenant.get(db, id=tenant_id)
    if db_tenant is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    # Если пытаемся изменить название, проверяем уникальность
    if tenant_changes.name is not None and tenant_changes.name != db_tenant.name:
        existing_tenant = await crud_tenant.get_by_name(db, name=tenant_changes.name)
        if existing_tenant:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Организация с таким названием уже существует",
            )
    
    try:
        updated_tenant = await crud_tenant.update(
            db,
            db_obj=db_tenant,
            name=tenant_changes.name,
            description=tenant_changes.description,
            active=tenant_changes.active  # <-- ПЕРЕДАЕМ active
        )
        await db.commit()
        await db.refresh(updated_tenant)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при обновлении организации: {str(e)}",
        )
    
    return TenantResponseSchema.model_validate(updated_tenant)


# ==========================================
# УДАЛЕНИЕ ОРГАНИЗАЦИИ
# ==========================================
@router.delete("/{tenant_id}", status_code=status.HTTP_200_OK)
async def delete_tenant(tenant_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Удаление организации (только если в ней нет пользователей)"""
    deleted_tenant = await crud_tenant.delete(db, id=tenant_id)
    
    if deleted_tenant is None:
        existing_tenant = await crud_tenant.get(db, id=tenant_id)
        if existing_tenant is None:
            raise HTTPException(status_code=404, detail="Organization not found")
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Невозможно удалить организацию: в ней есть пользователи. Сначала удалите всех пользователей.",
            )
    
    await db.commit()
    
    return {
        "status": "success",
        "message": f"Organization {deleted_tenant.name} successfully deleted",
    }