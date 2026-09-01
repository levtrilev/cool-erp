# app/core/auth/dependencies.py
from typing import Any
from fastapi import HTTPException, status, Depends
from app.core.auth.security import get_current_session  #, Cookie

async def require_admin(current_user: dict[str, dict[str, Any]] = Depends(get_current_session)) -> dict[str, dict[str, Any]]:
    """Зависимость для проверки прав администратора"""
    if not current_user.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для выполнения операции администратора"
        )
    return current_user

async def require_superadmin(current_user: dict[str, dict[str, Any]] = Depends(get_current_session)) -> dict[str, dict[str, Any]]:
    """Зависимость для проверки прав суперадминистратора"""
    if not current_user.get("is_superadmin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для выполнения операции суперадминистратора"
        )
    return current_user