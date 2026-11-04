"""backend/app/core/tenant/router.py"""
from typing import Optional
import uuid

from fastapi import APIRouter, HTTPException, status

from app.core.auth.dependencies import CurrentUser, DBSession
from app.core.schemas import ApiResponse, PaginatedResponse
from app.core.tenants.crud import crud_tenant
from app.core.tenants.schemas import (
    TenantCreateSchema,
    TenantResponseSchema,
    TenantUpdateSchema,
)

router = APIRouter(prefix="/tenants", tags=["Tenants"])


# ==================================================================
# ПОЛУЧЕНИЕ СПИСКА ОРГАНИЗАЦИЙ
# ==================================================================
@router.get(
    "/",
    response_model=ApiResponse[PaginatedResponse[TenantResponseSchema]],
)
async def read_tenants(
    db: DBSession,
    session: CurrentUser,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    active_only: bool = False,
) -> ApiResponse[PaginatedResponse[TenantResponseSchema]]:
    """
    Получение списка организаций с пагинацией, поиском и фильтром по активности.

    Права:
    - Суперадмин видит все организации.
    - Обычный пользователь видит только свою организацию.
    """
    items, total = await crud_tenant.get_multi_paginated(
        db,
        user_tenant_id=session.tenant_id,
        skip=skip,
        limit=limit,
        search=search,
        active_only=active_only,
        user_is_superadmin=session.is_superadmin,
    )

    return ApiResponse(
        success=True,
        message="Организации получены",
        data=PaginatedResponse(
            items=[TenantResponseSchema.model_validate(item) for item in items],
            total=total,
            page=(skip // limit) + 1,
            size=limit,
        ),
    )


# ==================================================================
# ПОЛУЧЕНИЕ ОДНОЙ ОРГАНИЗАЦИИ
# ==================================================================
@router.get(
    "/{tenant_id}",
    response_model=ApiResponse[TenantResponseSchema],
)
async def read_tenant(
    tenant_id: uuid.UUID,
    db: DBSession,
    session: CurrentUser,  # ✅ НОВОЕ: аутентификация обязательна
) -> ApiResponse[TenantResponseSchema]:
    """
    Получение одной организации по UUID.

    Права:
    - Суперадмин видит любую организацию.
    - Обычный пользователь видит только свою организацию.
    """
    # ✅ Проверка прав: обычный пользователь не может запросить чужую организацию
    if not session.is_superadmin and session.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к другой организации",
        )

    db_tenant = await crud_tenant.get(db, id=tenant_id)
    if db_tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Организация не найдена",
        )

    return ApiResponse(
        success=True,
        message="Организация получена",
        data=TenantResponseSchema.model_validate(db_tenant),
    )


# ==================================================================
# СОЗДАНИЕ ОРГАНИЗАЦИИ
# ==================================================================
@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[TenantResponseSchema],
)
async def create_tenant(
    tenant_in: TenantCreateSchema,
    db: DBSession,
    session: CurrentUser,  # ✅ НОВОЕ: аутентификация обязательна
) -> ApiResponse[TenantResponseSchema]:
    """
    Создание новой организации.

    Права:
    - Только суперадмин может создавать организации напрямую.
    - Публичная регистрация (создание организации первым пользователем)
      выполняется через /users/public/register.
    """
    # ✅ Проверка прав: только суперадмин
    if not session.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Создание организаций доступно только суперадмину. "
            "Для регистрации новой организации используйте /users/public/register",
        )

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
            active=tenant_in.active,
        )
        await db.commit()
        await db.refresh(new_tenant)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при создании организации: {str(e)}",
        )

    return ApiResponse(
        success=True,
        message="Организация создана",
        data=TenantResponseSchema.model_validate(new_tenant),
    )


# ==================================================================
# ОБНОВЛЕНИЕ ОРГАНИЗАЦИИ
# ==================================================================
@router.put(
    "/{tenant_id}",
    response_model=ApiResponse[TenantResponseSchema],
)
async def update_tenant(
    tenant_id: uuid.UUID,
    tenant_changes: TenantUpdateSchema,
    db: DBSession,
    session: CurrentUser,  # ✅ НОВОЕ: аутентификация обязательна
) -> ApiResponse[TenantResponseSchema]:
    """
    Обновление данных организации.

    Права:
    - Суперадмин может изменять любую организацию.
    - Администратор организации может изменять свою организацию.
    - Обычный пользователь не может изменять организации.
    """
    # ✅ Проверка прав: суперадмин или админ данной организации
    if not session.is_superadmin:
        if session.tenant_id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет доступа к другой организации",
            )
        if not session.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Изменение организации доступно только администратору",
            )

    db_tenant = await crud_tenant.get(db, id=tenant_id)
    if db_tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Организация не найдена",
        )

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
            active=tenant_changes.active,
        )
        await db.commit()
        await db.refresh(updated_tenant)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при обновлении организации: {str(e)}",
        )

    return ApiResponse(
        success=True,
        message="Организация обновлена",
        data=TenantResponseSchema.model_validate(updated_tenant),
    )


# ==================================================================
# УДАЛЕНИЕ ОРГАНИЗАЦИИ
# ==================================================================
@router.delete(
    "/{tenant_id}",
    status_code=status.HTTP_200_OK,
    response_model=ApiResponse[dict[str, str]],
)
async def delete_tenant(
    tenant_id: uuid.UUID,
    db: DBSession,
    session: CurrentUser,  # ✅ НОВОЕ: аутентификация обязательна
) -> ApiResponse[dict[str, str]]:
    """
    Удаление организации (только если в ней нет пользователей).

    Права:
    - Только суперадмин может удалять организации.
    """
    # ✅ Проверка прав: только суперадмин
    if not session.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Удаление организаций доступно только суперадмину",
        )

    deleted_tenant = await crud_tenant.delete(db, id=tenant_id)
    if deleted_tenant is None:
        existing_tenant = await crud_tenant.get(db, id=tenant_id)
        if existing_tenant is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Организация не найдена",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Невозможно удалить организацию: в ней есть пользователи. "
                "Сначала удалите всех пользователей.",
            )

    await db.commit()

    return ApiResponse(
        success=True,
        message=f"Организация {deleted_tenant.name} успешно удалена",
        data={"deleted_tenant_name": deleted_tenant.name},
    )