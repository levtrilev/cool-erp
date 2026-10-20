import uuid

from fastapi import APIRouter, HTTPException

from app.core.schemas import ApiResponse, PaginatedResponse
from app.core.auth.dependencies import DBSession, CurrentUser
from app.core.permissions.crud import crud_permission
from app.core.permissions.schemas import (
    PermissionCreateSchema,
    PermissionUpdateSchema,
    PermissionResponseSchema,
)

# ✅ КРИТИЧНО: Эта строка обязательна! Без неё main.py не сможет импортировать router
router = APIRouter(prefix="/permissions", tags=["Permissions"])


@router.get(
    "/",
    response_model=ApiResponse[PaginatedResponse[PermissionResponseSchema]]
)
async def get_permissions(
    db: DBSession,
    session: CurrentUser,
    skip: int = 0,
    limit: int = 100,
    search: str | None = None,
    role_id: uuid.UUID | None = None,
):
    """Получение списка полномочий."""
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
    db: DBSession,
    session: CurrentUser,
):
    """Получение одного полномочия по ID."""
    perm = await crud_permission.get_permission(
        db,
        item_id=permission_id,
        current_tenant_id=session.tenant_id,
        is_superadmin=session.is_superadmin,
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
    db: DBSession,
    session: CurrentUser,
):
    """Создание нового полномочия."""
    permission = await crud_permission.create_permission(
        db,
        obj_in=data,
        current_tenant_id=session.tenant_id,
        is_superadmin=session.is_superadmin,
    )

    await db.commit()
    await db.refresh(permission)

    return ApiResponse(
        success=True,
        message="Полномочие успешно создано",
        data=PermissionResponseSchema.model_validate(permission),
    )


@router.put("/{permission_id}", response_model=ApiResponse[PermissionResponseSchema])
async def update_permission(
    permission_id: uuid.UUID,
    data: PermissionUpdateSchema,
    db: DBSession,
    session: CurrentUser,
):
    """Обновление существующего полномочия."""
    perm = await crud_permission.update_permission(
        db,
        item_id=permission_id,
        obj_in=data,
        current_tenant_id=session.tenant_id,
        is_superadmin=session.is_superadmin,
    )

    await db.commit()
    await db.refresh(perm)

    return ApiResponse(
        success=True,
        message="Полномочие успешно обновлено",
        data=PermissionResponseSchema.model_validate(perm),
    )


@router.delete("/{permission_id}", response_model=ApiResponse[PermissionResponseSchema])
async def delete_permission(
    permission_id: uuid.UUID,
    db: DBSession,
    session: CurrentUser,
):
    """Удаление полномочия."""
    perm = await crud_permission.delete_permission(
        db,
        item_id=permission_id,
        current_tenant_id=session.tenant_id,
        is_superadmin=session.is_superadmin,
    )

    await db.commit()

    return ApiResponse(
        success=True,
        message="Полномочие успешно удалено",
        data=PermissionResponseSchema.model_validate(perm),
    )