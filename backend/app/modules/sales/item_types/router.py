# backend/app/modules/sales/item_types/router.py
"""
Роутер типов номенклатуры: 7 эндпоинтов (Правило №40, часть 7.1).
GET    /sales/item-types/                 — список
POST   /sales/item-types/                 — создание
GET    /sales/item-types/{item_type_id}   — одна запись
PUT    /sales/item-types/{item_type_id}   — сохранение (409/423)
DELETE /sales/item-types/{item_type_id}   — мягкое удаление
POST   /sales/item-types/{item_type_id}/lock
DELETE /sales/item-types/{item_type_id}/lock
"""
import uuid
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import cast as typing_cast

from fastapi import APIRouter, HTTPException, status

from app.core.access.schemas import UserProtocol
from app.core.auth.dependencies import CurrentUser, DBSession
from app.core.schemas import ApiResponse, PaginatedResponse, SortOrder
from app.modules.sales.item_types.crud import crud_sales_item_type
from app.modules.sales.item_types.exceptions import (
    SalesItemTypeEditingLockedError,
    SalesItemTypeNotFoundError,
    SalesItemTypePermissionError,
    SalesItemTypeVersionConflictError,
    SectionNotInTenantError,
)
from app.modules.sales.item_types.schemas import (
    SalesItemTypeCreateSchema,
    SalesItemTypeResponseSchema,
    SalesItemTypeSortField,
    SalesItemTypeUpdateSchema,
)

router = APIRouter(prefix="/sales/item-types", tags=["sales-item-types"])


def _parse_vat_filter(value: str | None) -> Decimal | None:
    """Числовой фильтр ставки НДС; некорректный ввод отклоняется явно (400)."""
    if value is None or value.strip() == "":
        return None
    try:
        return Decimal(value.strip().replace(",", "."))
    except InvalidOperation as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Некорректное числовое значение фильтра ставки НДС",
        ) from exc


@router.get(
    "/",
    response_model=ApiResponse[PaginatedResponse[SalesItemTypeResponseSchema]],
)
async def get_sales_item_types(
    current_session: CurrentUser,
    db: DBSession,
    skip: int = 0,
    limit: int = 15,
    search: str | None = None,
    sort_by: SalesItemTypeSortField | None = None,
    sort_order: SortOrder = SortOrder.ASC,
    filter_name: str | None = None,
    filter_item_class: str | None = None,
    filter_vat_rate: str | None = None,
    filter_doc_number: str | None = None,
    filter_updated_at: datetime | None = None,
) -> ApiResponse[PaginatedResponse[SalesItemTypeResponseSchema]]:
    """Список типов номенклатуры с контролем доступа, сортировкой и фильтрами."""
    items, total = await crud_sales_item_type.get_multi(
        db,
        user=typing_cast(UserProtocol, current_session),
        tenant_id=current_session.tenant_id,
        is_superadmin=bool(current_session.is_superadmin),
        skip=skip,
        limit=limit,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        filter_name=filter_name,
        filter_item_class=filter_item_class,
        filter_vat_rate=_parse_vat_filter(filter_vat_rate),
        filter_doc_number=filter_doc_number,
        filter_updated_at=filter_updated_at,
    )
    paginated = PaginatedResponse[SalesItemTypeResponseSchema](
        items=[SalesItemTypeResponseSchema.model_validate(i) for i in items],
        total=total,
        page=(skip // limit) + 1 if limit > 0 else 1,
        size=limit,
    )
    return ApiResponse(success=True, message="Типы номенклатуры получены", data=paginated)


@router.get(
    "/{item_type_id}", response_model=ApiResponse[SalesItemTypeResponseSchema]
)
async def get_sales_item_type(
    item_type_id: uuid.UUID,
    current_session: CurrentUser,
    db: DBSession,
) -> ApiResponse[SalesItemTypeResponseSchema]:
    row = await crud_sales_item_type.get_for_user(
        db,
        item_type_id=item_type_id,
        user=typing_cast(UserProtocol, current_session),
        tenant_id=current_session.tenant_id,
        is_superadmin=bool(current_session.is_superadmin),
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Тип номенклатуры не найден"
        )
    return ApiResponse(
        success=True,
        message="Тип номенклатуры получен",
        data=SalesItemTypeResponseSchema.model_validate(row),
    )


@router.post(
    "/",
    response_model=ApiResponse[SalesItemTypeResponseSchema],
    status_code=status.HTTP_201_CREATED,
)
async def create_sales_item_type(
    obj_in: SalesItemTypeCreateSchema,
    current_session: CurrentUser,
    db: DBSession,
) -> ApiResponse[SalesItemTypeResponseSchema]:
    try:
        row = await crud_sales_item_type.create_for_user(
            db,
            obj_in=obj_in,
            user=typing_cast(UserProtocol, current_session),
            tenant_id=current_session.tenant_id,
            is_superadmin=bool(current_session.is_superadmin),
        )
    except SectionNotInTenantError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except SalesItemTypePermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    await db.commit()
    await db.refresh(row)
    return ApiResponse(
        success=True,
        message="Тип номенклатуры создан",
        data=SalesItemTypeResponseSchema.model_validate(row),
    )


@router.put(
    "/{item_type_id}", response_model=ApiResponse[SalesItemTypeResponseSchema]
)
async def update_sales_item_type(
    item_type_id: uuid.UUID,
    obj_in: SalesItemTypeUpdateSchema,
    current_session: CurrentUser,
    db: DBSession,
) -> ApiResponse[SalesItemTypeResponseSchema]:
    try:
        row = await crud_sales_item_type.save_with_version(
            db,
            item_type_id=item_type_id,
            obj_in=obj_in,
            user=typing_cast(UserProtocol, current_session),
            tenant_id=current_session.tenant_id,
            user_id=typing_cast(UserProtocol, current_session).id,
            is_superadmin=bool(current_session.is_superadmin),
        )
    except SalesItemTypeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except SalesItemTypeVersionConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except SalesItemTypeEditingLockedError as exc:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=str(exc)) from exc
    except SalesItemTypePermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except SectionNotInTenantError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await db.commit()
    await db.refresh(row)
    return ApiResponse(
        success=True,
        message="Тип номенклатуры сохранён",
        data=SalesItemTypeResponseSchema.model_validate(row),
    )


@router.delete(
    "/{item_type_id}", response_model=ApiResponse[SalesItemTypeResponseSchema]
)
async def delete_sales_item_type(
    item_type_id: uuid.UUID,
    current_session: CurrentUser,
    db: DBSession,
) -> ApiResponse[SalesItemTypeResponseSchema]:
    try:
        row = await crud_sales_item_type.mark_deleted(
            db,
            item_type_id=item_type_id,
            user=typing_cast(UserProtocol, current_session),
            tenant_id=current_session.tenant_id,
            user_id=typing_cast(UserProtocol, current_session).id,
            is_superadmin=bool(current_session.is_superadmin),
        )
    except SalesItemTypeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except SalesItemTypeEditingLockedError as exc:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=str(exc)) from exc
    await db.commit()
    return ApiResponse(
        success=True,
        message="Тип номенклатуры удалён",
        data=SalesItemTypeResponseSchema.model_validate(row),
    )


@router.post(
    "/{item_type_id}/lock", response_model=ApiResponse[SalesItemTypeResponseSchema]
)
async def acquire_sales_item_type_lock(
    item_type_id: uuid.UUID,
    current_session: CurrentUser,
    db: DBSession,
) -> ApiResponse[SalesItemTypeResponseSchema]:
    try:
        row = await crud_sales_item_type.acquire_editing_lock(
            db,
            item_type_id=item_type_id,
            user=typing_cast(UserProtocol, current_session),
            tenant_id=current_session.tenant_id,
            user_id=typing_cast(UserProtocol, current_session).id,
            is_superadmin=bool(current_session.is_superadmin),
        )
    except SalesItemTypeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except SalesItemTypeEditingLockedError as exc:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=str(exc)) from exc
    except SalesItemTypePermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    await db.commit()
    await db.refresh(row)
    return ApiResponse(
        success=True,
        message="Блокировка захвачена",
        data=SalesItemTypeResponseSchema.model_validate(row),
    )


@router.delete(
    "/{item_type_id}/lock", response_model=ApiResponse[SalesItemTypeResponseSchema]
)
async def release_sales_item_type_lock(
    item_type_id: uuid.UUID,
    current_session: CurrentUser,
    db: DBSession,
) -> ApiResponse[SalesItemTypeResponseSchema]:
    try:
        row = await crud_sales_item_type.release_editing_lock(
            db,
            item_type_id=item_type_id,
            user=typing_cast(UserProtocol, current_session),
            tenant_id=current_session.tenant_id,
            user_id=typing_cast(UserProtocol, current_session).id,
            is_superadmin=bool(current_session.is_superadmin),
        )
    except SalesItemTypeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except SalesItemTypeEditingLockedError as exc:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=str(exc)) from exc
    await db.commit()
    await db.refresh(row)
    return ApiResponse(
        success=True,
        message="Блокировка освобождена",
        data=SalesItemTypeResponseSchema.model_validate(row),
    )