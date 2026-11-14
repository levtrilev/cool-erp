"""backend/app/core/roles/router.py"""
import logging
import uuid

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.core.audit import service as audit_service
from app.core.auth.dependencies import CurrentUser, DBSession
from app.core.roles.crud import crud_role
from app.core.roles.schemas import (
    RoleCreateSchema,
    RoleUpdateSchema,
    RoleResponseSchema,
    RoleSaveSchema,
)
from app.core.roles.services import role_service
from app.core.schemas import ApiResponse, PaginatedResponse
from app.core.users.models import UserModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/roles", tags=["Roles"])


@router.get("/", response_model=ApiResponse[PaginatedResponse[RoleResponseSchema]])
async def get_roles(
    db: DBSession,
    session: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, gt=0, le=1000),   # ✅ защита от ZeroDivisionError
    search: str | None = None,
) -> ApiResponse[PaginatedResponse[RoleResponseSchema]]:
    """Получение списка ролей с пагинацией и поиском."""
    is_superadmin = bool(session.is_superadmin)

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
) -> ApiResponse[RoleResponseSchema]:
    """Получение одной роли по ID."""
    is_superadmin = bool(session.is_superadmin)

    role = await crud_role.get(
        db,
        item_id=role_id,
        current_tenant_id=session.tenant_id,
        is_superadmin=is_superadmin,
    )
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Роль не найдена")

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
) -> ApiResponse[RoleResponseSchema]:
    """Создание новой роли."""
    is_superadmin = bool(session.is_superadmin)

    try:
        role = await crud_role.create(
            db, data=data, current_tenant_id=session.tenant_id, is_superadmin=is_superadmin
        )

        # ✅ Аудит создания — в той же транзакции, через сервис
        await audit_service.log_data_create(
            db,
            tenant_id=role.tenant_id,
            user_id=session.id,
            entity_type="role",
            entity_id=role.id,
            entity_name=role.name,
            changes=data.model_dump(mode="json"),
        )


        await db.commit()          # ✅ ОДИН коммит на всё
        await db.refresh(role)
    except HTTPException:
        await db.rollback()
        raise
    except Exception as exc:
        await db.rollback()
        logger.error("Ошибка создания роли: %s", str(exc), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ошибка создания роли",
        ) from exc

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
) -> ApiResponse[RoleResponseSchema]:
    """Обновление существующей роли."""
    is_superadmin = bool(session.is_superadmin)

    role_before = await crud_role.get(
        db,
        item_id=role_id,
        current_tenant_id=session.tenant_id,
        is_superadmin=is_superadmin,
    )
    if role_before is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Роль не найдена")

    # ✅ old_values собираем ДО crud_role.update — иначе diff будет old == new
    old_values: dict[str, uuid.UUID | str | list[uuid.UUID] | None] = {}
    dump = data.model_dump(exclude_unset=True)
    for field in RoleUpdateSchema.model_fields:
        if field in dump:
            old_values[field] = getattr(role_before, field, None)

    try:
        role = await crud_role.update(
            db,
            item_id=role_id,
            data=data,
            current_tenant_id=session.tenant_id,
            is_superadmin=is_superadmin,
        )

        # ✅ Аудит обновления — в той же транзакции, через сервис
        await audit_service.log_data_update(
            db,
            tenant_id=role.tenant_id,
            user_id=session.id,
            entity_type="role",
            entity_id=role.id,
            entity_name=role.name,
            old_values=old_values,
            new_values=dump,
        )


        await db.commit()          # ✅ ОДИН коммит (даже если changes пустой)
        await db.refresh(role)
    except HTTPException:
        await db.rollback()
        raise
    except Exception as exc:
        await db.rollback()
        logger.error("Ошибка обновления роли %s: %s", role_id, str(exc), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ошибка обновления роли",
        ) from exc

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
) -> ApiResponse[RoleResponseSchema]:
    """Удаление роли (каскадно удалит все её permissions)."""
    is_superadmin = bool(session.is_superadmin)

    existing_role = await crud_role.get(
        db,
        item_id=role_id,
        current_tenant_id=session.tenant_id,
        is_superadmin=is_superadmin,
    )
    if not existing_role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Роль не найдена")

    try:
        # Очищаем роль из массивов role_ids у всех пользователей
        users_stmt = select(UserModel).where(
            UserModel.role_ids.isnot(None),
            UserModel.role_ids.contains([role_id]),
        )
        users_result = await db.execute(users_stmt)
        affected_users: list[UserModel] = list(users_result.scalars().all())

        for user in affected_users:
            if user.role_ids:
                user.role_ids = [rid for rid in user.role_ids if rid != role_id]

        deleted_role = await crud_role.delete(
            db,
            item_id=role_id,
            current_tenant_id=session.tenant_id,
            is_superadmin=is_superadmin,
        )

        # ✅ Аудит удаления — в той же транзакции, через сервис
        await audit_service.log_data_delete(
            db,
            tenant_id=deleted_role.tenant_id,
            user_id=session.id,
            entity_type="role",
            entity_id=deleted_role.id,
            entity_name=deleted_role.name,
        )


        await db.commit()          # ✅ ОДИН коммит: users + role + audit
    except HTTPException:
        await db.rollback()
        raise
    except Exception as exc:
        await db.rollback()
        logger.error("Ошибка удаления роли %s: %s", role_id, str(exc), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ошибка удаления роли",
        ) from exc

    return ApiResponse(
        success=True,
        message="Роль удалена",
        data=RoleResponseSchema.model_validate(deleted_role),
    )


@router.post("/save", response_model=ApiResponse[RoleResponseSchema], status_code=201)
async def save_role(
    data: RoleSaveSchema,
    db: DBSession,
    session: CurrentUser,
    role_id: uuid.UUID | None = None,
) -> ApiResponse[RoleResponseSchema]:
    """Агрегированное сохранение роли: создание/обновление + синхронизация полномочий и пользователей."""
    is_superadmin = bool(session.is_superadmin)

    # ✅ old_values собираем ДО role_service.save_role
    old_values: dict[str, uuid.UUID | str | list[uuid.UUID] | None] = {}
    if role_id:
        role_before = await crud_role.get(
            db,
            item_id=role_id,
            current_tenant_id=session.tenant_id,
            is_superadmin=is_superadmin,
        )
        if role_before is not None:
            dump = data.model_dump(exclude_unset=True)
            for field in RoleSaveSchema.model_fields:
                if field in dump:
                    old_values[field] = getattr(role_before, field, None)

    try:
        role = await role_service.save_role(
            db,
            data=data,
            current_tenant_id=session.tenant_id,
            is_superadmin=is_superadmin,
            role_id=role_id,
        )

        action = "update" if role_id else "create"

        if action == "create":
            await audit_service.log_data_create(
                db,
                tenant_id=role.tenant_id,
                user_id=session.id,
                entity_type="role",
                entity_id=role.id,
                entity_name=role.name,
                changes=data.model_dump(mode="json"),
            )
        else:
            await audit_service.log_data_update(
                db,
                tenant_id=role.tenant_id,
                user_id=session.id,
                entity_type="role",
                entity_id=role.id,
                entity_name=role.name,
                old_values=old_values,
                new_values=data.model_dump(exclude_unset=True),
            )



        await db.commit()          # ✅ ОДИН коммит
        await db.refresh(role)
    except HTTPException:
        await db.rollback()
        raise
    except Exception as exc:
        await db.rollback()
        logger.error("Ошибка сохранения роли: %s", str(exc), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ошибка сохранения роли",
        ) from exc

    return ApiResponse(
        success=True,
        message="Роль и её полномочия успешно сохранены",
        data=RoleResponseSchema.model_validate(role),
    )