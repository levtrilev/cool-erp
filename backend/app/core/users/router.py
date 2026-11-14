"""backend/app/core/users/router.py"""
import logging
import uuid
from typing import Any, Mapping, cast

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import text as sql_text

from app.core.audit import service as audit_service
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
    "/public/register",
    status_code=status.HTTP_201_CREATED,
    response_model=PublicRegisterResponseSchema,
)
async def public_register(
    user_in: PublicRegisterSchema,
    db: DBSession,
) -> PublicRegisterResponseSchema:
    """Публичная регистрация гостя (создаёт нового пользователя + возможно нового тенанта)."""
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

        # ✅ Аудит создания — в той же транзакции
        await audit_service.log_data_create(
            db,
            tenant_id=new_user.tenant_id,
            user_id=new_user.id,   # публичная регистрация — «действие самого пользователя»
            entity_type="user",
            entity_id=new_user.id,
            entity_name=new_user.email,
            changes={
                "name": new_user.name,
                "email": new_user.email,
                "tenant_id": str(new_user.tenant_id),
                "is_new_tenant": is_new_tenant,
            },
        )


        await db.commit()
        await db.refresh(new_user)
    except Exception as e:
        await db.rollback()
        logger.error("Ошибка при регистрации: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при регистрации: {str(e)}",
        )

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
        # CRUD только flush — транзакцией управляет роутер (Правило №40 ч.8.1)
        new_user = await crud_user.register_new_user(db, user_in=user_in)

        # ✅ Аудит создания — в той же транзакции
        await audit_service.log_data_create(
            db,
            tenant_id=new_user.tenant_id,
            user_id=session.id,
            entity_type="user",
            entity_id=new_user.id,
            entity_name=new_user.email,
            changes={
                "name": new_user.name,
                "email": new_user.email,
                "tenant_id": str(new_user.tenant_id),
                "is_admin": new_user.is_admin,
                "is_superadmin": new_user.is_superadmin,
            },
        )


        await db.commit()
        await db.refresh(new_user)
    except Exception as e:
        await db.rollback()
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
    skip: int = Query(0, ge=0),
    limit: int = Query(100, gt=0, le=1000),   # ✅ gt=0 — защита от ZeroDivisionError
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
            page=(skip // limit) + 1,   # ✅ limit > 0 гарантирован Query(gt=0)
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

    # ✅ old_values собираем ДО crud.update_user — иначе diff будет old == new
    old_values: dict[str, uuid.UUID | str | bool | None] = {}
    for field in UserUpdateSchema.model_fields:
        if field in user_changes.model_dump(exclude_unset=True):
            old_values[field] = getattr(db_user, field, None)

    try:
        # ✅ CRUD возвращает (user, trigger_logout)
        updated_user, trigger_logout = await crud_user.update_user(
            db, db_user=db_user, user_changes=user_changes
        )

        # ✅ Аудит — в той же транзакции, через сервис
        await audit_service.log_data_update(
            db,
            tenant_id=updated_user.tenant_id,
            user_id=session.id,
            entity_type="user",
            entity_id=updated_user.id,
            entity_name=updated_user.email,
            old_values=old_values,
            new_values=user_changes.model_dump(exclude_unset=True),
        )


        await db.commit()
        await db.refresh(updated_user)

        # ✅ ПОСЛЕ commit — только теперь безопасно чистить сессии
        if trigger_logout:
            crud_user.clear_user_sessions(updated_user.id)
    except Exception as e:
        await db.rollback()
        logger.error("Ошибка обновления пользователя %s: %s", user_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ошибка обновления. Возможно ошибка БД.",
        )

    return ApiResponse(
        success=True,
        message="Пользователь обновлён",
        data=UserResponseSchema.model_validate(updated_user),
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

    # Снимок до удаления (для ответа клиенту)
    user_snapshot = UserResponseSchema.model_validate(deleted_user)
    user_name = deleted_user.name
    user_id_for_audit = deleted_user.id
    tenant_id_for_audit = deleted_user.tenant_id

    try:
        result = await crud_user.remove(db, id=user_id)
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден",
            )

        # ✅ Аудит — в той же транзакции, через сервис
        await audit_service.log_data_delete(
            db,
            tenant_id=tenant_id_for_audit,
            user_id=session.id,
            entity_type="user",
            entity_id=user_id_for_audit,
            entity_name=user_name,
        )


        await db.commit()

        # ✅ ПОСЛЕ commit — только теперь безопасно чистить сессии
        crud_user.clear_user_sessions(user_id_for_audit)
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error("Ошибка удаления пользователя %s: %s", user_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка удаления пользователя",
        )

    return ApiResponse(
        success=True,
        message=f"Пользователь {user_name} успешно удалён",
        data=user_snapshot,
    )