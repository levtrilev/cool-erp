"""FastAPI роутер для регионов с блокировками (Правило №40, часть 7).

✅ Архитектурные решения:
- Проверка доступа делегирована в AccessService (через CRUD)
- Список: AccessService.build_access_filter (кросс-организационная видимость)
- Один документ: AccessService.resolve_access (полная проверка)
- Редактирование/удаление: проверка уровня доступа и can_delete
- Блокировки: захват/освобождение с проверкой права на редактирование
"""

from typing import cast
import uuid

from fastapi import APIRouter, HTTPException

from app.core.access.schemas import ACCESS_LEVEL_AUTHOR, UserProtocol
from app.core.auth.dependencies import DBSession, CurrentUser
from app.core.schemas import ApiResponse, PaginatedResponse
from app.modules.sales.regions.crud import (
    crud_region,
    RegionEditingLockedError,
    RegionNotFoundError,
    RegionVersionConflictError,
)
from app.modules.sales.regions.schemas import (
    SalesRegionCreateSchema,
    SalesRegionResponseSchema,
    SalesRegionUpdateSchema,
)
from app.modules.sales.regions.service import region_service

router = APIRouter(
    prefix="/sales/regions",
    tags=["Sales: regions"],
)


# ==================================================================
# СПИСОК
# ==================================================================


@router.get(
    "/",
    response_model=ApiResponse[PaginatedResponse[SalesRegionResponseSchema]],
)
async def list_regions(
    db: DBSession,
    session: CurrentUser,
    skip: int = 0,
    limit: int = 100,
    search: str | None = None,
) -> ApiResponse[PaginatedResponse[SalesRegionResponseSchema]]:
    """
    Список регионов с фильтрацией через AccessService.

    ✅ AccessService.build_access_filter() обеспечивает:
    - Кросс-организационную видимость для раздела «Общий» (ТЗ §4.3.1)
    - Фильтрацию по ролям и permissions (ТЗ §3.2, §3.4)
    - Тег-проверку на уровне SQL (ТЗ §6)
    - Фильтрация выполняется на уровне SQL (ТЗ §3.1.4)
    """
    items, total = await crud_region.get_multi(
        db,
        user=cast(UserProtocol, session),
        skip=skip,
        limit=limit,
        search=search,
    )
    return ApiResponse(
        success=True,
        message="Регионы получены",
        data=PaginatedResponse(
            items=[SalesRegionResponseSchema.model_validate(i) for i in items],
            total=total,
            page=(skip // limit) + 1,
            size=limit,
        ),
    )


# ==================================================================
# СОЗДАНИЕ
# ==================================================================


@router.post(
    "/",
    response_model=ApiResponse[SalesRegionResponseSchema],
)
async def create_region(
    data: SalesRegionCreateSchema,
    db: DBSession,
    session: CurrentUser,
) -> ApiResponse[SalesRegionResponseSchema]:
    """
    Создание региона.

    Обработка ошибок:
    - 403: попытка создания в платформенном разделе не суперадмином (ТЗ §4.3.6)
    - 400: раздел не найден или иные ошибки валидации
    """
    try:
        region = await region_service.create(
            db,
            obj_in=data,
            user=cast(UserProtocol, session),
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # ✅ Правило №40, часть 8.1: commit выполняется в роутере
    await db.commit()
    await db.refresh(region)
    return ApiResponse(
        success=True,
        message="Регион создан",
        data=SalesRegionResponseSchema.model_validate(region),
    )


# ==================================================================
# ОДИН ДОКУМЕНТ
# ==================================================================


@router.get(
    "/{region_id}",
    response_model=ApiResponse[SalesRegionResponseSchema],
)
async def get_region(
    region_id: uuid.UUID,
    db: DBSession,
    session: CurrentUser,
) -> ApiResponse[SalesRegionResponseSchema]:
    """
    Один регион с полной проверкой доступа через AccessService.

    ✅ Возвращает 404, если документ не существует для пользователя
    (ТЗ §2.3, §2.6: скрытые записи не возвращаются).
    """
    region = await crud_region.get_for_user(
        db,
        region_id=region_id,
        user=cast(UserProtocol, session),
    )
    if region is None:
        raise HTTPException(status_code=404, detail="Регион не найден")

    return ApiResponse(
        success=True,
        message="Регион получен",
        data=SalesRegionResponseSchema.model_validate(region),
    )


# ==================================================================
# ОБНОВЛЕНИЕ
# ==================================================================


@router.put(
    "/{region_id}",
    response_model=ApiResponse[SalesRegionResponseSchema],
)
async def update_region(
    region_id: uuid.UUID,
    data: SalesRegionUpdateSchema,
    db: DBSession,
    session: CurrentUser,
) -> ApiResponse[SalesRegionResponseSchema]:
    """
    Сохранение с проверкой:
    - Уровня доступа (нужен >= 2 для редактирования)
    - Оптимистической блокировки (409)
    - Пессимистической блокировки (423)
    """
    # ✅ Проверяем право на редактирование через AccessService
    access_result = await crud_region.check_edit_access(
        db,
        region_id=region_id,
        user=cast(UserProtocol, session),
    )
    if access_result is None:
        # Документ не существует для пользователя (ТЗ §2.3)
        raise HTTPException(status_code=404, detail="Регион не найден")

    if access_result.level < ACCESS_LEVEL_AUTHOR:
        # ✅ ТЗ §5.4: право на чтение есть, но недостаточный уровень
        # для изменения → режим «только чтение»
        # ✅ ТЗ §4.3.3: в разделе «Общий» все кроме суперадмина — только чтение
        raise HTTPException(
            status_code=423,
            detail="Недостаточно прав для редактирования региона",
        )

    try:
        region = await region_service.update(
            db,
            region_id=region_id,
            obj_in=data,
            user=cast(UserProtocol, session),
        )
    except RegionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RegionVersionConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except RegionEditingLockedError as exc:
        raise HTTPException(status_code=423, detail=str(exc)) from exc
    except PermissionError as exc:
        # Попытка переместить в платформенный раздел не суперадмином
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    await db.commit()
    await db.refresh(region)
    return ApiResponse(
        success=True,
        message="Регион обновлён",
        data=SalesRegionResponseSchema.model_validate(region),
    )


# ==================================================================
# УДАЛЕНИЕ
# ==================================================================


@router.delete(
    "/{region_id}",
    response_model=ApiResponse[SalesRegionResponseSchema],
)
async def delete_region(
    region_id: uuid.UUID,
    db: DBSession,
    session: CurrentUser,
) -> ApiResponse[SalesRegionResponseSchema]:
    """
    Мягкое удаление с проверкой блокировки (423) и права на удаление.

    ✅ ТЗ §5.2: can_delete = false → удаление запрещено
    ✅ ТЗ §4.3.3: в разделе «Общий» can_delete всегда false для не-суперадмина
    """
    # Проверяем право на удаление через AccessService
    access_result = await crud_region.check_edit_access(
        db,
        region_id=region_id,
        user=cast(UserProtocol, session),
    )
    if access_result is None:
        raise HTTPException(status_code=404, detail="Регион не найден")

    if not access_result.can_delete:
        raise HTTPException(
            status_code=423,
            detail="Нет прав на удаление региона",
        )

    try:
        region = await region_service.delete(
            db,
            region_id=region_id,
            user=cast(UserProtocol, session),
        )
    except RegionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RegionEditingLockedError as exc:
        raise HTTPException(status_code=423, detail=str(exc)) from exc

    await db.commit()
    return ApiResponse(
        success=True,
        message="Регион удалён",
        data=SalesRegionResponseSchema.model_validate(region),
    )


# ==================================================================
# БЛОКИРОВКИ РЕДАКТИРОВАНИЯ (Правило №40, часть 7.1)
# ==================================================================


@router.post(
    "/{region_id}/lock",
    response_model=ApiResponse[SalesRegionResponseSchema],
)
async def acquire_region_lock(
    region_id: uuid.UUID,
    db: DBSession,
    session: CurrentUser,
) -> ApiResponse[SalesRegionResponseSchema]:
    """
    Захват пессимистической блокировки редактирования.

    ✅ Перед захватом проверяется право на редактирование.
    Если уровень < 2 (автор) — блокировка не захватывается,
    документ будет открыт в режиме «только чтение» (ТЗ §5.4).
    """
    # Проверяем право на редактирование перед захватом блокировки
    access_result = await crud_region.check_edit_access(
        db,
        region_id=region_id,
        user=cast(UserProtocol, session),
    )
    if access_result is None:
        raise HTTPException(status_code=404, detail="Регион не найден")

    if access_result.level < ACCESS_LEVEL_AUTHOR:
        raise HTTPException(
            status_code=423,
            detail="Недостаточно прав для редактирования региона",
        )

    try:
        region = await crud_region.acquire_editing_lock(
            db,
            region_id=region_id,
            user=cast(UserProtocol, session),
        )
    except RegionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RegionEditingLockedError as exc:
        raise HTTPException(status_code=423, detail=str(exc)) from exc

    await db.commit()
    await db.refresh(region)
    return ApiResponse(
        success=True,
        message="Блокировка захвачена",
        data=SalesRegionResponseSchema.model_validate(region),
    )


@router.delete(
    "/{region_id}/lock",
    response_model=ApiResponse[SalesRegionResponseSchema],
)
async def release_region_lock(
    region_id: uuid.UUID,
    db: DBSession,
    session: CurrentUser,
) -> ApiResponse[SalesRegionResponseSchema]:
    """Освобождение пессимистической блокировки редактирования."""
    try:
        region = await crud_region.release_editing_lock(
            db,
            region_id=region_id,
            user=cast(UserProtocol, session),
        )
    except RegionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RegionEditingLockedError as exc:
        raise HTTPException(status_code=423, detail=str(exc)) from exc

    await db.commit()
    await db.refresh(region)
    return ApiResponse(
        success=True,
        message="Блокировка освобождена",
        data=SalesRegionResponseSchema.model_validate(region),
    )
