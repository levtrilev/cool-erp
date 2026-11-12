"""backend/app/core/users/router.py"""
import logging
import uuid
from typing import Any, Mapping, cast

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text as sql_text

from app.core.audit.utils import get_entity_name
from app.core.auth.dependencies import CurrentUser, DBSession
from app.core.schemas import ApiResponse, PaginatedResponse
from app.core.users.crud import crud_user
from app.core.users.registration_service import registration_service
from app.core.users.schemas import (
    PublicRegisterResponseSchema,
    PublicRegisterSchema,
    TagUserResponseSchema,
    TagWithUsersResponseSchema,
    UserRegisterSchema,
    UserResponseSchema,
    UserUpdateSchema,
)
from app.core.access.schemas import UserProtocol

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["Users"])


# ==================================================================
# ПУБЛИЧНАЯ РЕГИСТРАЦИЯ
# ==================================================================
@router.post(
    "/public/register",  # ✅ Исправлено: убран пробел в пути
    status_code=status.HTTP_201_CREATED,
    response_model=PublicRegisterResponseSchema,
)
async def public_register(
    user_in: PublicRegisterSchema,
    db: DBSession,
) -> PublicRegisterResponseSchema:
    """Публичная регистрация гостя."""
    existing_user = await crud_user.get_by_email(db, email=user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=[
                {
                    "loc": ["body", "email"],
                    "msg": "Пользователь с таким email уже существует",
                    "type": "value_error",
                }
            ],
        )

    try:
        new_user, is_new_tenant = await registration_service.register(
            db, user_in=user_in
        )
    except Exception as e:
        await db.rollback()
        logger.error("Ошибка при регистрации: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при регистрации: {str(e)}",
        )

    await db.commit()
    await db.refresh(new_user)

    return PublicRegisterResponseSchema(
        id=new_user.id,
        name=new_user.name,
        email=new_user.email,
        tenant_id=new_user.tenant_id,
        is_admin=new_user.is_admin,
        is_superadmin=new_user.is_superadmin or False,
        is_new_tenant=is_new_tenant,
        tenant_name=user_in.tenant_name,
    )


# ==================================================================
# РЕГИСТРАЦИЯ ПОЛЬЗОВАТЕЛЯ АДМИНИСТРАТОРОМ
# ==================================================================
@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[UserResponseSchema],
)
async def register(
    user_in: UserRegisterSchema,
    db: DBSession,
    session: CurrentUser,
) -> ApiResponse[UserResponseSchema]:
    """Регистрация нового пользователя администратором или суперадмином."""
    if not session.is_admin and not session.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Создание пользователей доступно только администратору или суперадмину",
        )

    if not session.is_superadmin and user_in.tenant_id != session.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к другой организации",
        )

    existing_user = await crud_user.get_by_email(db, email=user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=[
                {
                    "loc": ["body", "email"],
                    "msg": "Пользователь с таким email уже существует",
                    "type": "value_error",
                }
            ],
        )

    try:
        # ⚠️ ЗАМЕЧАНИЕ: crud_user.register_new_user делает commit внутри.
        # Это нарушение Правила №40 ч.8.1, но исправление требует
        # изменения CRUD, что выходит за рамки Этапа 1.
        new_user = await crud_user.register_new_user(db, user_in=user_in)
    except Exception as e:
        logger.error("Ошибка создания пользователя: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ошибка создания. Возможно tenant_id не существует в вашей БД.",
        )

    return ApiResponse(
        success=True,
        message="Пользователь создан",
        data=UserResponseSchema.model_validate(new_user),
    )


# ==================================================================
# СПИСОК ПОЛЬЗОВАТЕЛЕЙ
# ==================================================================
@router.get(
    "/",
    response_model=ApiResponse[PaginatedResponse[UserResponseSchema]],
)
async def read_users(
    db: DBSession,
    session: CurrentUser,
    tenant_id: uuid.UUID | None = None,
    skip: int = 0,
    limit: int = 100,
    search: str | None = None,
) -> ApiResponse[PaginatedResponse[UserResponseSchema]]:
    """Получение списка пользователей с пагинацией."""
    is_superadmin: bool = bool(session.is_superadmin)

    if tenant_id and not is_superadmin:
        tenant_id = session.tenant_id

    items, total = await crud_user.get_multi_paginated(
        db,
        tenant_id=session.tenant_id,
        skip=skip,
        limit=limit,
        search=search,
        user_is_superadmin=is_superadmin,
        target_tenant_id=tenant_id,
    )

    return ApiResponse(
        success=True,
        message="Пользователи получены",
        data=PaginatedResponse[UserResponseSchema](
            items=[UserResponseSchema.model_validate(item) for item in items],
            total=total,
            page=(skip // limit) + 1,
            size=limit,
        ),
    )


# ==================================================================
# ТЕГИ С ПОЛЬЗОВАТЕЛЯМИ
# ==================================================================
@router.get(
    "/tags",
    response_model=ApiResponse[list[TagWithUsersResponseSchema]],
)
async def get_tags_with_users(
    db: DBSession,
    session: CurrentUser,
) -> ApiResponse[list[TagWithUsersResponseSchema]]:
    """Список тегов доступа и пользователей."""
    is_superadmin: bool = bool(session.is_superadmin)

    where_clause: str
    params: Mapping[str, Any]

    if is_superadmin:
        where_clause = ""
        params = {}
    else:
        where_clause = "WHERE u.tenant_id = :tenant_id"
        params = {"tenant_id": session.tenant_id}

    query = sql_text(f"""
        SELECT
            distinct_tags.tag AS tag,
            json_agg(
                json_build_object(
                    'id', u.id,
                    'name', u.name,
                    'email', u.email,
                    'tenant_id', u.tenant_id,
                    'tenant_name', t.name,
                    'tags', COALESCE(u.tags, ARRAY[]::varchar[])
                ) ORDER BY u.name
            ) AS users
        FROM (
            SELECT DISTINCT unnest(u0.tags) AS tag
            FROM public.users AS u0
            WHERE u0.tags IS NOT NULL
              AND array_length(u0.tags, 1) > 0
        ) AS distinct_tags
        JOIN public.users AS u
            ON u.tags @> ARRAY[distinct_tags.tag]::varchar[]
        LEFT JOIN public.tenants AS t
            ON t.id = u.tenant_id
        {where_clause}
        GROUP BY distinct_tags.tag
        ORDER BY distinct_tags.tag
    """)

    result = await db.execute(query, params)
    rows = result.all()

    items: list[TagWithUsersResponseSchema] = []
    for row in rows:
        raw_users: list[dict[str, Any]] = list(row.users or [])
        users = [TagUserResponseSchema.model_validate(u) for u in raw_users]
        items.append(TagWithUsersResponseSchema(tag=row.tag, users=users))

    return ApiResponse(
        success=True,
        message="Теги получены",
        data=items,
    )


# ==================================================================
# ОДИН ПОЛЬЗОВАТЕЛЬ
# ==================================================================
@router.get(
    "/{user_id}",
    response_model=ApiResponse[UserResponseSchema],
)
async def read_user(
    user_id: uuid.UUID,
    db: DBSession,
    session: CurrentUser,
) -> ApiResponse[UserResponseSchema]:
    """Получение одного пользователя по UUID."""
    db_user = await crud_user.get(db, id=user_id)
    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )

    if not session.is_superadmin:
        if db_user.id != cast(UserProtocol, session).id:
            if not session.is_admin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Нет доступа к профилю другого пользователя",
                )
            if db_user.tenant_id != session.tenant_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Нет доступа к пользователю другой организации",
                )

    return ApiResponse(
        success=True,
        message="Пользователь получен",
        data=UserResponseSchema.model_validate(db_user),
    )


# ==================================================================
# ОБНОВЛЕНИЕ ПОЛЬЗОВАТЕЛЯ
# ==================================================================
@router.put(
    "/{user_id}",
    response_model=ApiResponse[UserResponseSchema],
)
async def update_user(
    user_id: uuid.UUID,
    user_changes: UserUpdateSchema,
    db: DBSession,
    session: CurrentUser,
) -> ApiResponse[UserResponseSchema]:
    """Обновление пользователя."""
    db_user = await crud_user.get(db, id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    if not session.is_superadmin:
        if db_user.id != cast(UserProtocol, session).id:
            if not session.is_admin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Нет доступа к профилю другого пользователя",
                )
            if db_user.tenant_id != session.tenant_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Нет доступа к пользователю другой организации",
                )

    if (
        user_changes.is_superadmin is not None
        and user_changes.is_superadmin
        and not session.is_superadmin
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Назначение суперадминистратора доступно только суперадмину",
        )

    if (
        user_changes.tenant_id is not None
        and user_changes.tenant_id != db_user.tenant_id
        and not session.is_superadmin
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Смена организации доступна только суперадмину",
        )

    if (
        user_changes.is_admin is not None
        and not session.is_admin
        and not session.is_superadmin
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Назначение администратора доступно только администратору или суперадмину",
        )

    if (
        user_changes.role_ids is not None
        and not session.is_admin
        and not session.is_superadmin
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Назначение ролей доступно только администратору или суперадмину",
        )

    old_values: dict[str, uuid.UUID | str | bool | None] = {}
    if db_user:
        for field in UserUpdateSchema.model_fields:
            if field in user_changes.model_dump(exclude_unset=True):
                old_values[field] = getattr(db_user, field, None)

    try:
        # ⚠️ ЗАМЕЧАНИЕ: crud_user.update_user делает commit внутри.
        # Это нарушение Правила №40 ч.8.1, но исправление требует
        # изменения CRUD, что выходит за рамки Этапа 1.
        updated_user = await crud_user.update_user(
            db, db_user=db_user, user_changes=user_changes
        )
    except Exception as e:
        logger.error("Ошибка обновления пользователя %s: %s", user_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ошибка обновления. Возможно ошибка БД.",
        )

    # ✅ СНИМОК
    updated_user_snapshot = UserResponseSchema.model_validate(updated_user)
    updated_user_id = updated_user.id
    updated_user_tenant_id = updated_user.tenant_id
    updated_user_email = updated_user.email

    # ✅ АУДИТ
    try:
        from app.core.audit.models import DataAuditLog
        changes: dict[str, dict[str, str]] = {}
        dump = user_changes.model_dump(exclude_unset=True)
        for field, new_value in dump.items():
            if field in old_values and old_values[field] != new_value:
                if field.endswith('_id'):
                    old_entity_id = uuid.UUID(str(old_values[field])) if old_values[field] else None
                    new_entity_id = uuid.UUID(str(new_value)) if new_value else None
                    if old_entity_id:
                        old_name = await get_entity_name(db, field[:-3], old_entity_id)
                    else:
                        old_name = ""
                    if new_entity_id:
                        new_name = await get_entity_name(db, field[:-3], new_entity_id)
                    else:
                        new_name = ""
                    changes[field] = {
                        "old": old_name if old_name else str(old_values[field]),
                        "new": new_name if new_name else str(new_value)
                    }
                else:
                    changes[field] = {"old": str(old_values[field]), "new": str(new_value)}

        if changes:
            audit_log = DataAuditLog(
                id=uuid.uuid4(),
                tenant_id=updated_user_tenant_id,
                user_id=session.id,
                entity_type="user",
                entity_id=updated_user_id,
                entity_name=updated_user_email,
                action="update",
                changes=changes if changes else None,
            )
            db.add(audit_log)
            await db.commit()
    except Exception as e:
        logger.warning(f"Could not write data audit: {e}")

    return ApiResponse(
        success=True,
        message="Пользователь обновлён",
        data=updated_user_snapshot,
    )


# ==================================================================
# УДАЛЕНИЕ ПОЛЬЗОВАТЕЛЯ
# ==================================================================
@router.delete(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
    response_model=ApiResponse[UserResponseSchema],
)
async def delete_user(
    user_id: uuid.UUID,
    db: DBSession,
    session: CurrentUser,
) -> ApiResponse[UserResponseSchema]:
    """Удаление пользователя из базы данных."""
    if not session.is_admin and not session.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Удаление пользователей доступно только администратору или суперадмину",
        )

    if user_id == cast(UserProtocol, session).id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя удалить собственный аккаунт",
        )

    deleted_user = await crud_user.get(db, id=user_id)
    if deleted_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )

    if not session.is_superadmin and deleted_user.tenant_id != session.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к пользователю другой организации",
        )

    # ✅ СНИМОК до удаления
    user_snapshot = UserResponseSchema.model_validate(deleted_user)
    user_name = deleted_user.name
    user_id_for_audit = deleted_user.id
    tenant_id_for_audit = deleted_user.tenant_id

    # ✅ УДАЛЕНИЕ
    result = await crud_user.remove(db, id=user_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )
    await db.commit()

    # ✅ АУДИТ
    try:
        from app.core.audit.models import DataAuditLog
        audit_log = DataAuditLog(
            id=uuid.uuid4(),
            tenant_id=tenant_id_for_audit,
            user_id=session.id,
            entity_type="user",
            entity_id=user_id_for_audit,
            action="delete",
            changes={"deleted": True},
        )
        db.add(audit_log)
        await db.commit()
    except Exception as e:
        logger.warning(f"Could not write data audit: {e}")

    return ApiResponse(
        success=True,
        message=f"Пользователь {user_name} успешно удалён",
        data=user_snapshot,
    )