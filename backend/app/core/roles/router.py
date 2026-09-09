import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.schemas import ApiResponse, PaginatedResponse
from app.core.auth.dependencies import get_current_session
from app.core.auth.models import (
    UserSession,
)  # Или UserModel, в зависимости от вашей реализации зависимости
from app.core.roles.crud import crud_role
from app.core.roles.schemas import (
    RoleCreateSchema,
    RoleUpdateSchema,
    RoleResponseSchema,
    RoleSaveSchema,  # ✅ Добавлено для агрегированного сохранения
)

from app.core.roles.services import (
    role_service,
)  # ✅ Добавлено для агрегированного сохранения

router = APIRouter(prefix="/roles", tags=["Roles"])


@router.get("/", response_model=ApiResponse[PaginatedResponse[RoleResponseSchema]])
async def get_roles(
    skip: int = 0,
    limit: int = 10,
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
    session: UserSession = Depends(get_current_session),
):
    """Получение списка ролей с пагинацией и поиском."""
    # ✅ ИСПРАВЛЕНО: Прямой доступ к атрибутам сессии (session - это уже объект пользователя/сессии)
    is_superadmin = session.is_superadmin if session else False

    items, total = await crud_role.get_multi(
        db,
        skip=skip,
        limit=limit,
        search=search,
        current_tenant_id=session.tenant_id,
        is_superadmin=is_superadmin,
    )

    paginated_data = PaginatedResponse(
        items=[RoleResponseSchema.model_validate(item) for item in items],
        total=total,
        page=(skip // limit) + 1,
        size=limit,
    )
    return ApiResponse(
        success=True,
        message="Роли успешно получены",
        data=paginated_data,
    )


@router.get("/{role_id}", response_model=ApiResponse[RoleResponseSchema])
async def get_role(
    role_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    session: UserSession = Depends(get_current_session),
):
    """Получение одной роли по ID."""
    # ✅ ИСПРАВЛЕНО: Убрали session.user
    is_superadmin = session.is_superadmin if session else False

    role = await crud_role.get(
        db,
        item_id=role_id,
        current_tenant_id=session.tenant_id,
        is_superadmin=is_superadmin,
    )
    if not role:
        raise HTTPException(status_code=404, detail="Роль не найдена")

    return ApiResponse(
        success=True,
        message="Роль успешно получена",
        data=RoleResponseSchema.model_validate(role),
    )


@router.post("/", response_model=ApiResponse[RoleResponseSchema], status_code=201)
async def create_role(
    data: RoleCreateSchema,
    db: AsyncSession = Depends(get_db),
    session: UserSession = Depends(get_current_session),
):
    """Создание новой роли."""
    # ✅ ИСПРАВЛЕНО: Убрали session.user
    is_superadmin = session.is_superadmin if session else False

    role = await crud_role.create(
        db, data=data, current_tenant_id=session.tenant_id, is_superadmin=is_superadmin
    )

    return ApiResponse(
        success=True,
        message="Роль успешно создана",
        data=RoleResponseSchema.model_validate(role),
    )


@router.put("/{role_id}", response_model=ApiResponse[RoleResponseSchema])
async def update_role(
    role_id: uuid.UUID,
    data: RoleUpdateSchema,
    db: AsyncSession = Depends(get_db),
    session: UserSession = Depends(get_current_session),
):
    """Обновление существующей роли."""
    # ✅ ИСПРАВЛЕНО: Убрали session.user
    is_superadmin = session.is_superadmin if session else False

    role = await crud_role.update(
        db,
        item_id=role_id,
        data=data,
        current_tenant_id=session.tenant_id,
        is_superadmin=is_superadmin,
    )

    return ApiResponse(
        success=True,
        message="Роль успешно обновлена",
        data=RoleResponseSchema.model_validate(role),
    )


@router.delete("/{role_id}", response_model=ApiResponse[RoleResponseSchema])
async def delete_role(
    role_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    session: UserSession = Depends(get_current_session),
):
    """Удаление роли (каскадно удалит все её permissions)."""
    # ✅ ИСПРАВЛЕНО: Убрали session.user
    is_superadmin = session.is_superadmin if session else False

    role = await crud_role.delete(
        db,
        item_id=role_id,
        current_tenant_id=session.tenant_id,
        is_superadmin=is_superadmin,
    )

    return ApiResponse(
        success=True,
        message="Роль успешно удалена",
        data=RoleResponseSchema.model_validate(role),
    )


# ==============================================================================
# ✅ НОВЫЙ ЭНДПОИНТ: Агрегированное сохранение (необходим для EditRoleModal)
# ==============================================================================
@router.post("/save", response_model=ApiResponse[RoleResponseSchema], status_code=201)
async def save_role(
    data: RoleSaveSchema,
    role_id: uuid.UUID | None = None,  # Если None - создание, иначе обновление
    db: AsyncSession = Depends(get_db),
    session: UserSession = Depends(get_current_session),
):
    """
    Агрегированное сохранение роли: создание/обновление роли + синхронизация полномочий и пользователей.
    """
    is_superadmin = session.is_superadmin if session else False

    role = await role_service.save_role(
        db,
        data=data,
        current_tenant_id=session.tenant_id,
        is_superadmin=is_superadmin,
        role_id=role_id,
    )

    return ApiResponse(
        success=True,
        message="Роль и её полномочия успешно сохранены",
        data=RoleResponseSchema.model_validate(role),
    )
