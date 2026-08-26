import uuid
from typing import Generic, TypeVar, Optional, Tuple, List, Any, Type, Protocol
from sqlalchemy import func
from sqlalchemy.orm import Mapped  # Импортируем Mapped из SQLAlchemy
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException
from pydantic import BaseModel

# 1. Создаем Протокол для SQLAlchemy моделей.
# Описываем протокол так, как это видит SQLAlchemy 2.0
class DeclarativeModelProtocol(Protocol):
    id: Mapped[uuid.UUID]  # Используем Mapped вместо голого uuid.UUID
    
    def __init__(self, **kwargs: Any) -> None: ...

# 2. Ограничиваем TypeVar с помощью созданного протокола
ModelType = TypeVar("ModelType", bound=DeclarativeModelProtocol)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):

    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def get(self, db: AsyncSession, id: uuid.UUID) -> Optional[ModelType]:
        # Ошибка reportUnknownMemberType исчезнет, так как id описан в Protocol
        result = await db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_multi_paginated(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        search_field: str = "name",
    ) -> Tuple[List[ModelType], int]:
        data_query = select(self.model)
        count_query = select(func.count()).select_from(self.model)

        if search and hasattr(self.model, search_field):
            # Используем явное приведение типов (cast), чтобы Pylance знал: 
            # динамический атрибут имеет тип SQLAlchemy InstrumentableAttribute (у которого есть .ilike())
            model_attr = getattr(self.model, search_field)
            
            # Безопасно вызываем .ilike(), проверив наличие метода через static-анализ
            if hasattr(model_attr, "ilike"):
                filter_condition = model_attr.ilike(f"%{search}%")
                data_query = data_query.where(filter_condition)
                count_query = count_query.where(filter_condition)

        count_result = await db.execute(count_query)
        # Явно указываем int, так как scalar_one() возвращает Any
        total: int = count_result.scalar_one()

        data_query = data_query.offset(skip).limit(limit)
        data_result = await db.execute(data_query)
        
        # Получаем типизированный список моделей
        items = list(data_result.scalars().all())

        return items, total

    async def create(
        self, db: AsyncSession, obj_in: CreateSchemaType
    ) -> ModelType:
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
            raise HTTPException(
                status_code=400, detail="Не удалось создать запись."
            )

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
            raise HTTPException(
                status_code=400, detail="Не удалось обновить запись."
            )

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
            raise HTTPException(
                status_code=400, detail="Не удалось удалить запись."
            )

# from typing import Any, Generic, List, Optional, Tuple, Type, TypeVar
# # , cast
# import uuid
# from fastapi import HTTPException
# from sqlalchemy import func, select
# from sqlalchemy.exc import SQLAlchemyError
# from sqlalchemy.ext.asyncio import AsyncSession
# # from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# ModelType = TypeVar("ModelType")
# CreateSchemaType = TypeVar("CreateSchemaType")
# UpdateSchemaType = TypeVar("UpdateSchemaType")


# class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):

#     def __init__(self, model: Type[ModelType]):
#         self.model = model

#     async def get(self, db: AsyncSession, id: uuid.UUID) -> Optional[ModelType]:
#         result = await db.execute(select(self.model).where(self.model.id == id))
#         return result.scalar_one_or_none()

#     async def get_multi_paginated(
#         self,
#         db: AsyncSession,
#         skip: int = 0,
#         limit: int = 100,
#         search: Optional[str] = None,
#         search_field: str = "name",
#     ) -> Tuple[List[ModelType], int]:
#         """Возвращает кортеж: (список_объектов, общее_количество_подходящих_записей)"""
#         # 1. Формируем базовые запросы для данных и для подсчета
#         data_query = select(self.model)
#         count_query = select(func.count()).select_from(self.model)

#         # 2. Динамически накладываем фильтр поиска, если он передан
#         if search and hasattr(self.model, search_field):
#             model_attr = getattr(self.model, search_field)
#             filter_condition = model_attr.ilike(f"%{search}%")

#             data_query = data_query.where(filter_condition)
#             count_query = count_query.where(filter_condition)

#         # 3. Выполняем подсчет общего количества (без учета offset/limit!)
#         count_result = await db.execute(count_query)
#         total = count_result.scalar_one()

#         # 4. Применяем пагинацию к основному запросу и получаем данные
#         data_query = data_query.offset(skip).limit(limit)
#         data_result = await db.execute(data_query)
#         items = data_result.scalars().all()

#         return items, total

#     async def create(
#         self, db: AsyncSession, obj_in: CreateSchemaType
#     ) -> ModelType:
#         obj_in_data = obj_in.model_dump()
#         db_obj = self.model(**obj_in_data)
#         db.add(db_obj)
#         try:
#             await db.commit()
#             await db.refresh(db_obj)
#             return db_obj
#         except SQLAlchemyError as e:
#             await db.rollback()
#             print(f"❌ Ошибка создания в {self.model.__name__}: {e}")
#             raise HTTPException(
#                 status_code=400, detail="Не удалось создать запись."
#             )

#     async def update(
#         self, db: AsyncSession, db_obj: ModelType, obj_in: UpdateSchemaType
#     ) -> ModelType:
#         update_data = (
#             obj_in.model_dump(exclude_unset=True)
#             if hasattr(obj_in, "model_dump")
#             else obj_in
#         )
#         for field in update_data:
#             if hasattr(db_obj, field):
#                 setattr(db_obj, field, update_data[field])
#         db.add(db_obj)
#         try:
#             await db.commit()
#             await db.refresh(db_obj)
#             return db_obj
#         except SQLAlchemyError as e:
#             await db.rollback()
#             print(f"❌ Ошибка обновления в {self.model.__name__}: {e}")
#             raise HTTPException(
#                 status_code=400, detail="Не удалось обновить запись."
#             )

#     async def remove(self, db: AsyncSession, id: Any) -> Optional[ModelType]:
#         db_obj = await self.get(db, id=id)
#         if not db_obj:
#             return None
#         await db.delete(db_obj)
#         try:
#             await db.commit()
#             return db_obj
#         except SQLAlchemyError as e:
#             await db.rollback()
#             print(f"❌ Ошибка удаления из {self.model.__name__}: {e}")
#             raise HTTPException(
#                 status_code=400, detail="Не удалось удалить запись."
#             )
