import uuid
import logging

# from typing import Generic, TypeVar, Optional, Tuple, List, Any, Type, Protocol
from typing import (
    Generic,
    TypeVar,
    Optional,
    Tuple,
    List,
    Any,
    Type,
    Protocol,
    Callable,
    Awaitable,
)
from functools import wraps

from sqlalchemy import func
from sqlalchemy.orm import Mapped  # Импортируем Mapped из SQLAlchemy
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from fastapi import HTTPException
from pydantic import BaseModel

logger = logging.getLogger("app.crud")


# 1. Создаем Протокол для SQLAlchemy моделей.
# Описываем протокол так, как это видит SQLAlchemy 2.0
class DeclarativeModelProtocol(Protocol):
    id: Mapped[uuid.UUID]  # Используем Mapped вместо голого uuid.UUID

    def __init__(self, **kwargs: Any) -> None: ...


# 2. Ограничиваем TypeVar с помощью созданного протокола
ModelType = TypeVar("ModelType", bound=DeclarativeModelProtocol)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


# 3. УНИВЕРСАЛЬНЫЙ ДЕКОРАТОР ДЛЯ ОБРАБОТКИ ОШИБОК БД
# ✅ TypeVar для типизации самой функции
F = TypeVar("F", bound=Callable[..., Awaitable[Any]])


def with_db_error_handling(action: str) -> Callable[[F], F]:
    """
    Декоратор для автоматической обработки ошибок БД в CRUD-методах.
    Делает rollback, логирует ошибку с именем модели и возвращает понятный HTTP 400/500.
    """

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(
            self: Any, db: AsyncSession, *args: Any, **kwargs: Any
        ) -> Any:
            model_name = self.model.__name__
            try:
                return await func(self, db, *args, **kwargs)

            except IntegrityError as e:
                await db.rollback()
                error_msg = str(e.orig).lower()

                if "unique" in error_msg or "duplicate" in error_msg:
                    detail = f"Нарушение уникальности: такая запись уже существует."
                elif "foreign key" in error_msg or "violates foreign key" in error_msg:
                    detail = f"Ошибка ссылки: связанная запись не найдена или удалена."
                elif "null value in column" in error_msg:
                    detail = f"Отсутствует обязательное поле."
                else:
                    detail = f"Ошибка целостности данных: {str(e.orig)}"

                logger.warning(f"[{model_name}.{action}] IntegrityError: {e.orig}")
                raise HTTPException(status_code=400, detail=detail)

            except SQLAlchemyError as e:
                await db.rollback()
                logger.error(
                    f"[{model_name}.{action}] SQLAlchemyError: {e}", exc_info=True
                )
                raise HTTPException(
                    status_code=500, detail="Внутренняя ошибка базы данных."
                )

            except Exception as e:
                await db.rollback()
                logger.error(
                    f"[{model_name}.{action}] Unexpected Error: {e}", exc_info=True
                )
                raise HTTPException(
                    status_code=500, detail="Непредвиденная ошибка сервера."
                )

        return wrapper  # type: ignore[return-value]

    return decorator


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):

    def __init__(self, model: Type[ModelType]):
        self.model = model

    @with_db_error_handling("get")
    async def get(self, db: AsyncSession, id: uuid.UUID) -> Optional[ModelType]:
        # Ошибка reportUnknownMemberType исчезнет, так как id описан в Protocol
        result = await db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    @with_db_error_handling("get_multi_paginated")
    async def get_multi_paginated(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        search_field: str = "name",
        user_is_superadmin: bool = False,
    ) -> Tuple[List[ModelType], int]:
        # Исправленный вариант
        if hasattr(self.model, "tenant_id") and not user_is_superadmin:
            # (если пользователь является суперадмином, то он видит все tenant-ы)
            # Использование getattr защищает от ошибок типизации (type checker видит это как Any)
            tenant_attr = getattr(self.model, "tenant_id")
            data_query = select(self.model).where(tenant_attr == tenant_id)
            count_query = (
                select(func.count())
                .select_from(self.model)
                .where(tenant_attr == tenant_id)
            )
        else:
            data_query = select(self.model)
            count_query = select(func.count()).select_from(self.model)

        if search and hasattr(self.model, search_field):
            # Используем явное приведение типов (cast), чтобы Pylance знал:
            # динамический атрибут имеет тип SQLAlchemy InstrumentableAttribute (у которого есть .ilike())
            model_attr = getattr(self.model, search_field)

            # Безопасно вызываем .ilike(), проверив наличие метода через static-анализ
            if hasattr(model_attr, "ilike"):
                filter_condition = model_attr.ilike(f"%{search}%")
                data_query = data_query
                count_query = count_query.where(filter_condition)

        count_result = await db.execute(count_query)
        # Явно указываем int, так как scalar_one() возвращает Any
        total: int = count_result.scalar_one()

        data_query = data_query.offset(skip).limit(limit)
        data_result = await db.execute(data_query)

        # Получаем типизированный список моделей
        items = list(data_result.scalars().all())

        return items, total

    # ✅ Декоратор автоматически перехватит ошибки, сделает rollback и красиво залоггирует
    @with_db_error_handling("create")
    async def create(self, db: AsyncSession, obj_in: CreateSchemaType) -> ModelType:
        # Благодаря bound=BaseModel, Pylance знает про метод model_dump()
        obj_in_data = obj_in.model_dump()

        # Благодаря конструктору в Protocol, создание объекта теперь валидно
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        try:
            await db.commit()
            await db.refresh(db_obj)
            return db_obj
        except SQLAlchemyError as e:
            await db.rollback()
            # Используем __name__ безопасно через обращение к типу
            print(f"❌ Ошибка создания в {self.model.__name__}: {e}")
            raise HTTPException(status_code=400, detail="Не удалось создать запись.")

    @with_db_error_handling("update")
    async def update(
        self, db: AsyncSession, db_obj: ModelType, obj_in: UpdateSchemaType
    ) -> ModelType:
        # Исключаем предупреждения: Pylance уверен, что obj_in — это BaseModel
        update_data = obj_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        db.add(db_obj)
        try:
            await db.commit()
            await db.refresh(db_obj)
            return db_obj
        except SQLAlchemyError as e:
            await db.rollback()
            print(f"❌ Ошибка обновления в {self.model.__name__}: {e}")
            raise HTTPException(status_code=400, detail="Не удалось обновить запись.")

    async def remove(self, db: AsyncSession, id: Any) -> Optional[ModelType]:
        # Передаем id. Так как get() ожидает uuid.UUID,
        # лучше использовать явную валидацию или оставить Any, если id бывает разных типов.
        db_obj = await self.get(db, id=id)
        if not db_obj:
            return None
        await db.delete(db_obj)
        try:
            await db.commit()
            return db_obj
        except SQLAlchemyError as e:
            await db.rollback()
            print(f"❌ Ошибка удаления из {self.model.__name__}: {e}")
            raise HTTPException(status_code=400, detail="Не удалось удалить запись.")
