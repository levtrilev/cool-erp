"""
Роутер справочника валют.
Чтение доступно всем аутентифицированным пользователям.
Запись — только суперадмину (глобальный справочник).
"""
import uuid

from fastapi import APIRouter, HTTPException

from app.core.auth.dependencies import CurrentUser, DBSession
from app.core.currencies.crud import crud_currency
from app.core.currencies.exceptions import (
    CurrencyCodeAlreadyExistsError,
    CurrencyNotFoundError,
)
from app.core.currencies.schemas import (
    CurrencyCreateSchema,
    CurrencyResponseSchema,
    CurrencyUpdateSchema,
)
from app.core.schemas import ApiResponse, PaginatedResponse

router = APIRouter(prefix="/currencies", tags=["currencies"])


@router.get("/", response_model=ApiResponse[PaginatedResponse[CurrencyResponseSchema]])
async def get_currencies(
    db: DBSession,
    session: CurrentUser,
    skip: int = 0,
    limit: int = 100,
    search: str | None = None,
    only_active: bool = False,
) -> ApiResponse[PaginatedResponse[CurrencyResponseSchema]]:
    """Список валют (Правило №4: обёртка для Orval)."""
    items, total = await crud_currency.get_multi(
        db, skip=skip, limit=limit, search=search, only_active=only_active
    )
    return ApiResponse(
        success=True,
        message="Валюты получены",
        data=PaginatedResponse(
            items=[CurrencyResponseSchema.model_validate(i) for i in items],
            total=total,
            page=(skip // limit) + 1,
            size=limit,
        ),
    )


@router.get("/{currency_id}", response_model=ApiResponse[CurrencyResponseSchema])
async def get_currency(
    currency_id: uuid.UUID,
    db: DBSession,
    session: CurrentUser,
) -> ApiResponse[CurrencyResponseSchema]:
    """Одна валюта по ID."""
    currency = await crud_currency.get(db, id=currency_id)
    if currency is None:
        raise HTTPException(status_code=404, detail="Валюта не найдена")
    return ApiResponse(
        success=True,
        message="Валюта получена",
        data=CurrencyResponseSchema.model_validate(currency),
    )


@router.post("/", response_model=ApiResponse[CurrencyResponseSchema], status_code=201)
async def create_currency(
    obj_in: CurrencyCreateSchema,
    db: DBSession,
    session: CurrentUser,
) -> ApiResponse[CurrencyResponseSchema]:
    """Создание валюты (только суперадмин)."""
    if not session.is_superadmin:
        raise HTTPException(
            status_code=403, detail="Только суперадмин может создавать валюты"
        )
    try:
        currency = await crud_currency.create_currency(db, obj_in=obj_in)
    except CurrencyCodeAlreadyExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await db.commit()
    await db.refresh(currency)
    return ApiResponse(
        success=True,
        message="Валюта создана",
        data=CurrencyResponseSchema.model_validate(currency),
    )


@router.put("/{currency_id}", response_model=ApiResponse[CurrencyResponseSchema])
async def update_currency(
    currency_id: uuid.UUID,
    obj_in: CurrencyUpdateSchema,
    db: DBSession,
    session: CurrentUser,
) -> ApiResponse[CurrencyResponseSchema]:
    """Обновление валюты (только суперадмин)."""
    if not session.is_superadmin:
        raise HTTPException(
            status_code=403, detail="Только суперадмин может изменять валюты"
        )
    try:
        currency = await crud_currency.update_currency(
            db, currency_id=currency_id, obj_in=obj_in
        )
    except CurrencyNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CurrencyCodeAlreadyExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await db.commit()
    await db.refresh(currency)
    return ApiResponse(
        success=True,
        message="Валюта обновлена",
        data=CurrencyResponseSchema.model_validate(currency),
    )


@router.delete("/{currency_id}", response_model=ApiResponse[CurrencyResponseSchema])
async def delete_currency(
    currency_id: uuid.UUID,
    db: DBSession,
    session: CurrentUser,
) -> ApiResponse[CurrencyResponseSchema]:
    """Удаление валюты (только суперадмин)."""
    if not session.is_superadmin:
        raise HTTPException(
            status_code=403, detail="Только суперадмин может удалять валюты"
        )
    try:
        currency = await crud_currency.delete_currency(db, currency_id=currency_id)
    except CurrencyNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await db.commit()
    return ApiResponse(
        success=True,
        message="Валюта удалена",
        data=CurrencyResponseSchema.model_validate(currency),
    )