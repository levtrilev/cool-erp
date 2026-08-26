# from uuid import UUID
# from typing import Optional
# from app.core.database import get_db
# from app.core.auth.crud import crud_user
# from fastapi import APIRouter, Depends, HTTPException
# from app.core.schemas import PaginatedResponse
# from sqlalchemy.ext.asyncio import AsyncSession

# from app.core.auth.schemas import UserResponseSchema

# router = APIRouter(prefix="/users", tags=["Users"])


# @router.get("/", response_model=PaginatedResponse[UserResponseSchema])
# async def read_users(
#     skip: int = 0,
#     limit: int = 100,
#     search: Optional[str] = None,
#     db: AsyncSession = Depends(get_db),
# ):
#     """Эндпоинт возвращает JSON вида: {"items": [...], "total": 1250}

#     Благодаря GIN-индексу в PostgreSQL, поиск по подстроке 'search' будет
#     отрабатывать за миллисекунды даже на больших объемах данных.
#     """
#     items, total = await crud_user.get_multi_paginated(
#         db, skip=skip, limit=limit, search=search
#     )

#     # FastAPI автоматически упакует этот словарь в схему PaginatedResponse
#     return {"items": items, "total": total}


# @router.get("/{user_id}", response_model=UserResponseSchema)
# async def read_user(user_id: UUID, db: AsyncSession = Depends(get_db)):
    # db_user = await crud_user.get(db, id=user_id)
    # if db_user is None:
    #     raise HTTPException(status_code=404, detail="User not found")
    # return db_user
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.crud import crud_user
# Импортируем новую схему обновления
from app.core.auth.schemas import UserResponseSchema, UserUpdateSchema
from app.core.database import get_db
from app.core.schemas import PaginatedResponse

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/", response_model=PaginatedResponse[UserResponseSchema])
async def read_users(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Получение списка пользователей с пагинацией и GIN-поиском."""
    items, total = await crud_user.get_multi_paginated(
        db, skip=skip, limit=limit, search=search
    )
    return {"items": items, "total": total}


@router.get("/{user_id}", response_model=UserResponseSchema)
async def read_user(user_id: UUID, db: AsyncSession = Depends(get_db)):
    """Получение одного пользователя по UUID."""
    db_user = await crud_user.get(db, id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


# @router.put("/{user_id}", response_model=UserResponseSchema)
# async def update_user(
#     user_id: UUID,
#     user_in: UserUpdateSchema,
#     db: AsyncSession = Depends(get_db),
# ):
#     """Обновление данных пользователя.

#     Использует универсальный метод .update() базового класса с авто-коммитом.
#     """
#     # 1. Проверяем, существует ли пользователь в базе данных
#     db_user = await crud_user.get(db, id=user_id)
#     if db_user is None:
#         raise HTTPException(status_code=404, detail="User not found")

#     # 2. Передаем объект из БД и схему обновлений в базовый CRUD.
#     # Он автоматически обновит измененные поля и сделает безопасный commit/rollback.
#     updated_user = await crud_user.update(db, db_obj=db_user, obj_in=user_in)
#     return updated_user



