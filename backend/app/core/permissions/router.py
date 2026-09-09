import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.schemas import ApiResponse, PaginatedResponse
from app.core.auth.dependencies import get_current_session
from app.core.auth.models import UserSession
from app.core.permissions.crud import crud_permission
from app.core.permissions.schemas import (
    PermissionCreateSchema,
    PermissionUpdateSchema,
    PermissionResponseSchema,
)

router = APIRouter(prefix="/permissions", tags=["Permissions"])

@router.get("/", response_model=ApiResponse[PaginatedResponse[PermissionResponseSchema]])
async def get_permissions(
    skip: int = 0,
    limit: int = 100, # Для полномочий обычно нужно больше на странице, т.к. это матрица
    search: str | None = None,
    role_id: uuid.UUID | None = None, # ✅ Специальный фильтр для экрана редактирования роли
    db: AsyncSession = Depends(get_db),
    session: UserSession = Depends(get_current_session),
):
    """Получение списка полномочий."""
    # user = session.user
    # is_superadmin = user.is_superadmin if user else False
    
    items, total = await crud_permission.get_multi(
        db,
        skip=skip,
        limit=limit,
        search=search,
        role_id=role_id,
        current_tenant_id=session.tenant_id,
        is_superadmin=session.is_superadmin,
    )
    
    paginated_data = PaginatedResponse(
            items=[PermissionResponseSchema.model_validate(item) for item in items],
            total=total,
            page=(skip // limit) + 1,
            size=limit,
        )

    return ApiResponse(
        success=True,
        message="Полномочия успешно получены",
        data=paginated_data,
    )


@router.get("/{permission_id}", response_model=ApiResponse[PermissionResponseSchema])
async def get_permission(
    permission_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    session: UserSession = Depends(get_current_session),
):
    """Получение одного полномочия по ID."""
    user = session.user
    is_superadmin = user.is_superadmin if user else False
    
    perm = await crud_permission.get(
        db, 
        item_id=permission_id, 
        current_tenant_id=session.tenant_id, 
        is_superadmin=is_superadmin
    )
    if not perm:
        raise HTTPException(status_code=404, detail="Полномочие не найдено")
        
    return ApiResponse(
        success=True,
        message="Полномочие успешно получено",
        data=PermissionResponseSchema.model_validate(perm),
    )


@router.post("/", response_model=ApiResponse[PermissionResponseSchema], status_code=201)
async def create_permission(
    data: PermissionCreateSchema,
    db: AsyncSession = Depends(get_db),
    session: UserSession = Depends(get_current_session),
):
    """Создание нового полномочия."""
    user = session.user
    is_superadmin = user.is_superadmin if user else False
    
    perm = await crud_permission.create(
        db, 
        data=data, 
        current_tenant_id=session.tenant_id, 
        is_superadmin=is_superadmin
    )
    
    return ApiResponse(
        success=True,
        message="Полномочие успешно создано",
        data=PermissionResponseSchema.model_validate(perm),
    )


@router.put("/{permission_id}", response_model=ApiResponse[PermissionResponseSchema])
async def update_permission(
    permission_id: uuid.UUID,
    data: PermissionUpdateSchema,
    db: AsyncSession = Depends(get_db),
    session: UserSession = Depends(get_current_session),
):
    """Обновление существующего полномочия."""
    user = session.user
    is_superadmin = user.is_superadmin if user else False
    
    perm = await crud_permission.update(
        db, 
        item_id=permission_id, 
        data=data, 
        current_tenant_id=session.tenant_id, 
        is_superadmin=is_superadmin
    )
    
    return ApiResponse(
        success=True,
        message="Полномочие успешно обновлено",
        data=PermissionResponseSchema.model_validate(perm),
    )


@router.delete("/{permission_id}", response_model=ApiResponse[PermissionResponseSchema])
async def delete_permission(
    permission_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    session: UserSession = Depends(get_current_session),
):
    """Удаление полномочия."""
    user = session.user
    is_superadmin = user.is_superadmin if user else False
    
    perm = await crud_permission.delete(
        db, 
        item_id=permission_id, 
        current_tenant_id=session.tenant_id, 
        is_superadmin=is_superadmin
    )
    
    return ApiResponse(
        success=True,
        message="Полномочие успешно удалено",
        data=PermissionResponseSchema.model_validate(perm),
    )