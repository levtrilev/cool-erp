# app/core/auth/dependencies.py
from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.security import get_current_session, get_db
from app.core.users.models import UserModel as User


async def require_admin(current_user: User = Depends(get_current_session)) -> User:
    """Зависимость для проверки прав администратора"""
    if not getattr(current_user, "is_admin", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для выполнения операции администратора"
        )
    return current_user


async def require_superadmin(current_user: User = Depends(get_current_session)) -> User:
    """Зависимость для проверки прав суперадминистратора"""
    if not getattr(current_user, "is_superadmin", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для выполнения операции суперадминистратора"
        )
    return current_user


# ✅ Аннотированные типы для использования в роутерах
SuperAdminUser = Annotated[User, Depends(require_superadmin)]
CurrentUser = Annotated[User, Depends(get_current_session)]
DBSession = Annotated[AsyncSession, Depends(get_db)]