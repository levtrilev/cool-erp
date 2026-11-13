"""
Роутер заказов продаж.

7 эндпоинтов (Правило №40, часть 7.1):
  GET    /sales-orders/                 — список (сортировка + фильтры)
  POST   /sales-orders/                 — создание
  GET    /sales-orders/{order_id}       — одна запись
  PUT    /sales-orders/{order_id}       — сохранение (409/423)
  DELETE /sales-orders/{order_id}       — мягкое удаление
  POST   /sales-orders/{order_id}/lock  — захват блокировки
  DELETE /sales-orders/{order_id}/lock  — освобождение блокировки
"""
import uuid
from datetime import date
from typing import cast as typing_cast

from fastapi import APIRouter, HTTPException, status

from app.core.access.schemas import UserProtocol
from app.core.auth.dependencies import CurrentUser, DBSession
from app.core.schemas import ApiResponse, PaginatedResponse, SortOrder
from app.modules.sales.orders.crud import crud_sales_order
from app.modules.sales.orders.exceptions import (
    DeliveryMethodInvalidError,
    SalesOrderAccessDeniedError,
    SalesOrderEditingLockedError,
    SalesOrderNotFoundError,
    SalesOrderPermissionError,
    SalesOrderVersionConflictError,
    SectionNotInTenantError,
)
from app.modules.sales.orders.schemas import (
    SalesOrderCreateSchema,
    SalesOrderResponseSchema,
    SalesOrderSortField,
    SalesOrderUpdateSchema,
)
from decimal import Decimal, InvalidOperation

router = APIRouter(prefix="/sales-orders", tags=["sales-orders"])

def _parse_amount_filter(value: str | None) -> Decimal | None:
    """
    Разбор числового фильтра суммы.
    Запятая принимается как десятичный разделитель (ru-RU ввод).
    Некорректное значение отклоняется явно (400), а не игнорируется:
    молчаливое игнорирование скрыло бы ошибку ввода от пользователя.
    """
    if value is None or value.strip() == "":
        return None
    normalized = value.strip().replace(",", ".")
    try:
        return Decimal(normalized)
    except InvalidOperation as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Некорректное числовое значение фильтра суммы",
        ) from exc


@router.get(
    "/",
    response_model=ApiResponse[PaginatedResponse[SalesOrderResponseSchema]],
)
async def get_sales_orders(
    current_session: CurrentUser,
    db: DBSession,
    skip: int = 0,
    limit: int = 15,
    search: str | None = None,
    sort_by: SalesOrderSortField | None = None,
    sort_order: SortOrder = SortOrder.ASC,
    filter_doc_number: str | None = None,
    filter_doc_date: date | None = None,
    filter_customer_name: str | None = None,
    filter_supplier_name: str | None = None,
    filter_doc_status: str | None = None,
    filter_updated_at: date | None = None,
    filter_total_amount: str | None = None,
) -> ApiResponse[PaginatedResponse[SalesOrderResponseSchema]]:
    """Список заказов с контролем доступа, сортировкой и фильтрацией."""
    items, total = await crud_sales_order.get_multi(
        db,
        user=typing_cast(UserProtocol, current_session),
        tenant_id=current_session.tenant_id,
        is_superadmin=current_session.is_superadmin,
        skip=skip,
        limit=limit,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        filter_doc_number=filter_doc_number,
        filter_doc_date=filter_doc_date,
        filter_customer_name=filter_customer_name,
        filter_supplier_name=filter_supplier_name,
        filter_doc_status=filter_doc_status,
        filter_updated_at=filter_updated_at,
        filter_total_amount=_parse_amount_filter(filter_total_amount),
    )
    paginated = PaginatedResponse[SalesOrderResponseSchema](
        items=[SalesOrderResponseSchema.model_validate(item) for item in items],
        total=total,
        page=(skip // limit) + 1 if limit > 0 else 1,
        size=limit,
    )
    return ApiResponse(
        success=True,
        message="Заказы получены",
        data=paginated,
    )

@router.get(
    "/{order_id}", response_model=ApiResponse[SalesOrderResponseSchema]
)
async def get_sales_order(
    order_id: uuid.UUID,
    current_session: CurrentUser,
    db: DBSession,
) -> ApiResponse[SalesOrderResponseSchema]:
    """Один заказ с проверкой доступа через AccessService."""
    order = await crud_sales_order.get_for_user(
        db,
        order_id=order_id,
        user=typing_cast(UserProtocol, current_session),
        tenant_id=current_session.tenant_id,
        is_superadmin=current_session.is_superadmin,
    )
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Заказ не найден"
        )
    return ApiResponse(
        success=True,
        message="Заказ получен",
        data=SalesOrderResponseSchema.model_validate(order),
    )


@router.post(
    "/",
    response_model=ApiResponse[SalesOrderResponseSchema],
    status_code=status.HTTP_201_CREATED,
)
async def create_sales_order(
    obj_in: SalesOrderCreateSchema,
    current_session: CurrentUser,
    db: DBSession,
) -> ApiResponse[SalesOrderResponseSchema]:
    """Создание заказа со строками спецификации."""
    try:
        order = await crud_sales_order.create_for_user(
            db,
            obj_in=obj_in,
            user=typing_cast(UserProtocol, current_session),
            tenant_id=current_session.tenant_id,
            is_superadmin=current_session.is_superadmin,
        )
    except SectionNotInTenantError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except DeliveryMethodInvalidError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except SalesOrderPermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc

    await db.commit()
    await db.refresh(order)
    return ApiResponse(
        success=True,
        message="Заказ создан",
        data=SalesOrderResponseSchema.model_validate(order),
    )


@router.put(
    "/{order_id}", response_model=ApiResponse[SalesOrderResponseSchema]
)
async def update_sales_order(
    order_id: uuid.UUID,
    obj_in: SalesOrderUpdateSchema,
    current_session: CurrentUser,
    db: DBSession,
) -> ApiResponse[SalesOrderResponseSchema]:
    """Сохранение с проверкой доступа, версии (409) и блокировки (423)."""
    try:
        order = await crud_sales_order.save_with_version(
            db,
            order_id=order_id,
            obj_in=obj_in,
            user=typing_cast(UserProtocol, current_session),
            tenant_id=current_session.tenant_id,
            user_id=typing_cast(UserProtocol, current_session).id,
            is_superadmin=current_session.is_superadmin,
        )
    except SalesOrderNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except SalesOrderVersionConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    except SalesOrderEditingLockedError as exc:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED, detail=str(exc)
        ) from exc
    except SalesOrderAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc
    except SalesOrderPermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc
    except SectionNotInTenantError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except DeliveryMethodInvalidError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    await db.commit()
    await db.refresh(order)
    return ApiResponse(
        success=True,
        message="Заказ сохранён",
        data=SalesOrderResponseSchema.model_validate(order),
    )


@router.delete(
    "/{order_id}", response_model=ApiResponse[SalesOrderResponseSchema]
)
async def delete_sales_order(
    order_id: uuid.UUID,
    current_session: CurrentUser,
    db: DBSession,
) -> ApiResponse[SalesOrderResponseSchema]:
    """Мягкое удаление с проверкой can_delete через AccessService."""
    try:
        order = await crud_sales_order.mark_deleted(
            db,
            order_id=order_id,
            user=typing_cast(UserProtocol, current_session),
            tenant_id=current_session.tenant_id,
            user_id=typing_cast(UserProtocol, current_session).id,
            is_superadmin=current_session.is_superadmin,
        )
    except SalesOrderNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except SalesOrderEditingLockedError as exc:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED, detail=str(exc)
        ) from exc
    except SalesOrderAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc

    await db.commit()
    return ApiResponse(
        success=True,
        message="Заказ удалён",
        data=SalesOrderResponseSchema.model_validate(order),
    )


@router.post(
    "/{order_id}/lock", response_model=ApiResponse[SalesOrderResponseSchema]
)
async def acquire_sales_order_lock(
    order_id: uuid.UUID,
    current_session: CurrentUser,
    db: DBSession,
) -> ApiResponse[SalesOrderResponseSchema]:
    """Захват пессимистической блокировки (423, если занято)."""
    try:
        order = await crud_sales_order.acquire_editing_lock(
            db,
            order_id=order_id,
            user=typing_cast(UserProtocol, current_session),
            tenant_id=current_session.tenant_id,
            user_id=typing_cast(UserProtocol, current_session).id,
            is_superadmin=current_session.is_superadmin,
        )
    except SalesOrderNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except SalesOrderEditingLockedError as exc:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED, detail=str(exc)
        ) from exc
    except SalesOrderAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc
    except SalesOrderPermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc

    await db.commit()
    await db.refresh(order)
    return ApiResponse(
        success=True,
        message="Блокировка захвачена",
        data=SalesOrderResponseSchema.model_validate(order),
    )


@router.delete(
    "/{order_id}/lock", response_model=ApiResponse[SalesOrderResponseSchema]
)
async def release_sales_order_lock(
    order_id: uuid.UUID,
    current_session: CurrentUser,
    db: DBSession,
) -> ApiResponse[SalesOrderResponseSchema]:
    """Освобождение пессимистической блокировки."""
    try:
        order = await crud_sales_order.release_editing_lock(
            db,
            order_id=order_id,
            user=typing_cast(UserProtocol, current_session),
            tenant_id=current_session.tenant_id,
            user_id=typing_cast(UserProtocol, current_session).id,
            is_superadmin=current_session.is_superadmin,
        )
    except SalesOrderNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except SalesOrderEditingLockedError as exc:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED, detail=str(exc)
        ) from exc

    await db.commit()
    await db.refresh(order)
    return ApiResponse(
        success=True,
        message="Блокировка освобождена",
        data=SalesOrderResponseSchema.model_validate(order),
    )