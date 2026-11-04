"""backend/app/core/users/router.py"""
import logging
import uuid
from typing import Any, Mapping, cast

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text as sql_text

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
# from app.core.tenants.crud import crud_tenant

logger = logging.getLogger(__name__)  # ✅ Исправлено: __name__ вместо name

router = APIRouter(prefix="/users", tags=["Users"])


# ==================================================================
# ПУБЛИЧНАЯ РЕГИСТРАЦИЯ (Умная логика + полная структура доступа)
# ==================================================================
@router.post(
    "/public/register",  # ✅ Исправлено: убран пробел в пути
    status_code=status.HTTP_201_CREATED,
    response_model=PublicRegisterResponseSchema,
)
async def public_register(
    user_in: PublicRegisterSchema,
    db: DBSession,  # ✅ Правило №32: аннотированный тип вместо Depends
) -> PublicRegisterResponseSchema:
    """
    Публичная регистрация гостя.
    - Если организация существует → рядовой пользователь.
    - Если не существует → новая организация + полная структура доступа:
      тенант, раздел «Общий-<Организация>», роль администратора,
      Permissions для всех активных doctype, пользователь с is_admin=True.
    """
    # 1. Проверяем, нет ли уже пользователя с таким email
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

    # 2. Регистрация через сервис (полная структура доступа)
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

    # 3. Commit в роутере (Правило №40, часть 8.1)
    await db.commit()
    await db.refresh(new_user)

    # 4. Формируем ответ
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
    db: DBSession,  # ✅ НОВОЕ: аутентификация обязательна
    session: CurrentUser,  # ✅ НОВОЕ: аутентификация обязательна
) -> ApiResponse[UserResponseSchema]:
    """
    Регистрация нового пользователя администратором или суперадмином.

    Права:
    - Администратор организации может создавать пользователей только
      в своей организации.
    - Суперадмин может создавать пользователей в любой организации.
    """
    # ✅ Проверка прав: только админ или суперадмин
    if not session.is_admin and not session.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Создание пользователей доступно только администратору "
            "или суперадмину",
        )

    # ✅ Проверка тенанта: админ не может создавать пользователей
    # в чужой организации
    if not session.is_superadmin and user_in.tenant_id != session.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к другой организации",
        )

    # Проверяем, нет ли уже пользователя с таким email
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
    db: DBSession,  # ✅ Правило №32
    session: CurrentUser,  # ✅ Правило №32
    tenant_id: uuid.UUID | None = None,
    skip: int = 0,
    limit: int = 100,
    search: str | None = None,
) -> ApiResponse[PaginatedResponse[UserResponseSchema]]:
    """
    Получение списка пользователей с пагинацией.

    Права:
    - Обычный пользователь: всегда видит только свою организацию.
    - Суперадмин без tenant_id: видит пользователей всех организаций.
    - Суперадмин с tenant_id: видит пользователей указанной организации.
    """
    is_superadmin: bool = bool(session.is_superadmin)

    # ✅ Правило №26: обычный админ не может запрашивать чужой тенант
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
        data=PaginatedResponse(
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
    """
    Список тегов доступа и пользователей, которым они присвоены.

    ТЗ RBAC_ABAC v2.1 §6.3.5:
    - Администратор видит только пользователей своей Организации
    - Суперадмин видит пользователей всех Организаций

    Фильтрация выполняется на уровне SQL (Правило №26).
    """
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
    db: DBSession,  # ✅ НОВОЕ: аутентификация обязательна
    session: CurrentUser,  # ✅ НОВОЕ: аутентификация обязательна
) -> ApiResponse[UserResponseSchema]:
    """
    Получение одного пользователя по UUID.

    Права:
    - Пользователь может видеть свой профиль.
    - Администратор может видеть пользователей своей организации.
    - Суперадмин может видеть любого пользователя.
    """
    db_user = await crud_user.get(db, id=user_id)
    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )

    # ✅ Проверка прав: свой профиль, админ своей организации или суперадмин
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
    db: DBSession,  # ✅ НОВОЕ: аутентификация обязательна
    session: CurrentUser,  # ✅ НОВОЕ: аутентификация обязательна
) -> ApiResponse[UserResponseSchema]:
    """
    Обновление пользователя.

    Права:
    - Пользователь может обновлять свой профиль.
    - Администратор может обновлять пользователей своей организации.
    - Суперадмин может обновлять любого пользователя.

    Ограничения:
    - Назначение суперадминистратора доступно только суперадмину.
    - Смена организации доступна только суперадмину.
    - Назначение администратора доступно только администратору или суперадмину.
    - Назначение ролей доступно только администратору или суперадмину.
    """
    db_user = await crud_user.get(db, id=user_id)
    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )

    # ✅ Проверка прав: свой профиль, админ своей организации или суперадмин
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

    # ✅ ЗАЩИТА: запрет повышения до суперадмина для не-суперадмина
    if (
        user_changes.is_superadmin is not None
        and user_changes.is_superadmin
        and not session.is_superadmin
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Назначение суперадминистратора доступно только суперадмину",
        )

    # ✅ ЗАЩИТА: запрет смены организации для не-суперадмина
    if (
        user_changes.tenant_id is not None
        and user_changes.tenant_id != db_user.tenant_id
        and not session.is_superadmin
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Смена организации доступна только суперадмину",
        )

    # ✅ ЗАЩИТА: запрет назначения администратора для не-админа/не-суперадмина
    if (
        user_changes.is_admin is not None
        and not session.is_admin
        and not session.is_superadmin
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Назначение администратора доступно только администратору "
            "или суперадмину",
        )

    # ✅ ЗАЩИТА: запрет назначения ролей для не-админа/не-суперадмина
    if (
        user_changes.role_ids is not None
        and not session.is_admin
        and not session.is_superadmin
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Назначение ролей доступно только администратору "
            "или суперадмину",
        )

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
    db: DBSession,  # ✅ НОВОЕ: аутентификация обязательна
    session: CurrentUser,  # ✅ НОВОЕ: аутентификация обязательна
) -> ApiResponse[UserResponseSchema]:
    """
    Удаление пользователя из базы данных.

    Права:
    - Только администратор или суперадмин может удалять пользователей.
    - Администратор может удалять только пользователей своей организации.
    - Суперадмин может удалять любого пользователя.
    - Нельзя удалить себя (защита от случайного удаления).
    """
    # ✅ Проверка прав: только админ или суперадмин
    if not session.is_admin and not session.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Удаление пользователей доступно только администратору "
            "или суперадмину",
        )

    # ✅ ЗАЩИТА: нельзя удалить себя
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

    # ✅ Проверка тенанта: админ не может удалять пользователей
    # чужой организации
    if not session.is_superadmin and deleted_user.tenant_id != session.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к пользователю другой организации",
        )

    # Удаляем пользователя
    result = await crud_user.remove(db, id=user_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )

    # ✅ Правило №40, часть 8.1: commit в роутере
    await db.commit()

    return ApiResponse(
        success=True,
        message=f"Пользователь {result.name} успешно удалён",
        data=UserResponseSchema.model_validate(result),
    )