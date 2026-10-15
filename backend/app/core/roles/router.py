import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.schemas import ApiResponse, PaginatedResponse
from app.core.auth.dependencies import CurrentUser, DBSession, get_current_session
from app.core.auth.models import UserSession
from app.core.roles.crud import crud_role
from app.core.roles.schemas import (
    RoleCreateSchema,
    RoleUpdateSchema,
    RoleResponseSchema,
    RoleSaveSchema,
)
from app.core.roles.services import role_service
from app.core.users.models import UserModel

router = APIRouter(prefix="/roles", tags=["Roles"])


@router.get("/", response_model=ApiResponse[PaginatedResponse[RoleResponseSchema]])
async def get_roles(
    db: DBSession,
    session: CurrentUser,  
    skip: int = 0,
    limit: int = 10,
    search: str | None = None,

):
    """Получение списка ролей с пагинацией и поиском."""
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
    db: DBSession,
    session: CurrentUser,  
):
    """Получение одной роли по ID."""
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
    db: DBSession,
    session: CurrentUser,  
):
    """Создание новой роли."""
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
    db: DBSession,
    session: CurrentUser,  
):
    """Обновление существующей роли."""
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
    db: DBSession,
    session: CurrentUser,   
):
    """Удаление роли (каскадно удалит все её permissions)."""
    is_superadmin = session.is_superadmin if session else False

    # 1. Проверяем существование роли (для корректного 404)
    existing_role = await crud_role.get(
        db,
        item_id=role_id,
        current_tenant_id=session.tenant_id,
        is_superadmin=is_superadmin,
    )
    if not existing_role:
        raise HTTPException(status_code=404, detail="Роль не найдена")

    # 2. ✅ Очищаем роль из массивов role_ids у всех пользователей
    # Связь в модели viewonly, поэтому каскадное удаление не сработает.
    # Важно: Здесь добавлена ИЗБЫТОЧНАЯ логика очистки users.role_ids. 
    # Поскольку связь RoleModel.users объявлена как viewonly=True 
    # (массив хранится на стороне пользователя), при удалении роли 
    # SQLAlchemy не удалит автоматически этот role_id из массивов пользователей. 
    # Если этого не сделать, у пользователей останутся "битые" ссылки на удалённую роль.
    # явного db.update(user) в коде нет. Это работает благодаря механизму автоматического 
    # отслеживания изменений (dirty tracking) в SQLAlchemy 2.0.

    # EditRoleModal запрещает удалять Роль, пока не удалены ее пользователи

    users_stmt = select(UserModel).where(
        UserModel.role_ids.isnot(None),
        UserModel.role_ids.contains([role_id]),
    )
    users_result = await db.execute(users_stmt)
    affected_users: list[UserModel] = list(users_result.scalars().all())

    for user in affected_users:
        if user.role_ids:
            user.role_ids = [rid for rid in user.role_ids if rid != role_id]

    # 3. Удаляем саму роль (внутри crud выполняется только flush)
    deleted_role = await crud_role.delete(
        db,
        item_id=role_id,
        current_tenant_id=session.tenant_id,
        is_superadmin=is_superadmin,
    )
    
    # role = await crud_role.delete(
    #     db,
    #     item_id=role_id,
    #     current_tenant_id=session.tenant_id,
    #     is_superadmin=is_superadmin,
    # )

    # 4. ✅ Явно фиксируем транзакцию удаления
    await db.commit()

    return ApiResponse(
        success=True,
        message="Роль удалена",
        data=RoleResponseSchema.model_validate(deleted_role),
    )


@router.post("/save", response_model=ApiResponse[RoleResponseSchema], status_code=201)
async def save_role(
    data: RoleSaveSchema,
    role_id: uuid.UUID | None = None,
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

# ==============================================================================
# ✅ ЭНДПОИНТЫ add_role_permission и remove_role_permission УДАЛЕНЫ.
# Управление полномочиями теперь осуществляется через модуль /permissions/
# ==============================================================================