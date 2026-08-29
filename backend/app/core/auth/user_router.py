
# from typing import Optional
# from uuid import UUID

# from fastapi import APIRouter, Depends, HTTPException
# from sqlalchemy.ext.asyncio import AsyncSession

# from app.core.auth.crud import crud_user
# # Импортируем новую схему обновления
# from app.core.auth.schemas import UserResponseSchema
# from app.core.database import get_db
# from app.core.schemas import PaginatedResponse

# router = APIRouter(prefix="/users", tags=["Users"])


# @router.get("/", response_model=PaginatedResponse[UserResponseSchema])
# async def read_users(
#     skip: int = 0,
#     limit: int = 100,
#     search: Optional[str] = None,
#     db: AsyncSession = Depends(get_db),
# ):
#     """Получение списка пользователей с пагинацией и GIN-поиском."""
#     items, total = await crud_user.get_multi_paginated(
#         db, skip=skip, limit=limit, search=search
#     )
#     return {"items": items, "total": total}


# @router.get("/{user_id}", response_model=UserResponseSchema)
# async def read_user(user_id: UUID, db: AsyncSession = Depends(get_db)):
#     """Получение одного пользователя по UUID."""
#     db_user = await crud_user.get(db, id=user_id)
#     if db_user is None:
#         raise HTTPException(status_code=404, detail="User not found")
#     return db_user





