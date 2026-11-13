"""
CRUD справочника валют.
Глобальный справочник: мультиарендная фильтрация не применяется (Правило №26).
"""
import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crud.base import CRUDBase
from app.core.currencies.exceptions import (
    CurrencyCodeAlreadyExistsError,
    CurrencyNotFoundError,
)
from app.core.currencies.models import CurrencyModel
from app.core.currencies.schemas import CurrencyCreateSchema, CurrencyUpdateSchema


class CRUDCurrency(
    CRUDBase[CurrencyModel, CurrencyCreateSchema, CurrencyUpdateSchema]
):
    """CRUD для глобального справочника валют."""

    def __init__(self) -> None:
        super().__init__(CurrencyModel)

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
        only_active: bool = False,
    ) -> tuple[list[CurrencyModel], int]:
        """Список валют с поиском по коду и названию."""
        stmt = select(CurrencyModel)
        count_stmt = select(func.count()).select_from(CurrencyModel)

        if only_active:
            stmt = stmt.where(CurrencyModel.is_active == True)  # noqa: E712
            count_stmt = count_stmt.where(CurrencyModel.is_active == True)  # noqa: E712

        if search:
            search_filter = or_(
                CurrencyModel.code.ilike(f"%{search}%"),
                CurrencyModel.name.ilike(f"%{search}%"),
            )
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)

        stmt = stmt.order_by(CurrencyModel.code.asc()).offset(skip).limit(limit)
        result = await db.execute(stmt)
        items = list(result.scalars().all())

        count_result = await db.execute(count_stmt)
        total = count_result.scalar_one()

        return items, total

    async def get_by_code(
        self, db: AsyncSession, *, code: str
    ) -> CurrencyModel | None:
        """Получение валюты по коду."""
        stmt = select(CurrencyModel).where(CurrencyModel.code == code)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_currency(
        self, db: AsyncSession, *, obj_in: CurrencyCreateSchema
    ) -> CurrencyModel:
        """Создание валюты с проверкой уникальности кода."""
        existing = await self.get_by_code(db, code=obj_in.code.upper())
        if existing is not None:
            raise CurrencyCodeAlreadyExistsError(
                f"Валюта с кодом {obj_in.code.upper()} уже существует"
            )
        return await self.create(db, obj_in=obj_in)

    async def update_currency(
        self,
        db: AsyncSession,
        *,
        currency_id: uuid.UUID,
        obj_in: CurrencyUpdateSchema,
    ) -> CurrencyModel:
        """Обновление валюты с проверкой уникальности кода."""
        currency = await self.get(db, id=currency_id)
        if currency is None:
            raise CurrencyNotFoundError("Валюта не найдена")

        # Если меняется код, проверяем уникальность
        if obj_in.code is not None and obj_in.code.upper() != currency.code:
            existing = await self.get_by_code(db, code=obj_in.code.upper())
            if existing is not None:
                raise CurrencyCodeAlreadyExistsError(
                    f"Валюта с кодом {obj_in.code.upper()} уже существует"
                )

        return await self.update(db, db_obj=currency, obj_in=obj_in)

    async def delete_currency(
        self, db: AsyncSession, *, currency_id: uuid.UUID
    ) -> CurrencyModel:
        """
        Удаление валюты.
        Для пилота — жёсткое удаление. В будущем можно заменить на мягкое
        (is_active = False) или проверять использование в документах.
        """
        currency = await self.get(db, id=currency_id)
        if currency is None:
            raise CurrencyNotFoundError("Валюта не найдена")
        await self.remove(db, id=currency_id)
        return currency


crud_currency = CRUDCurrency()