# backend/app/core/user_preferences/router.py
"""Роутер персональных настроек интерфейса."""
from typing import cast as typing_cast

from fastapi import APIRouter

from app.core.auth.dependencies import CurrentUser, DBSession
from app.core.schemas import ApiResponse
from app.core.user_preferences.schemas import (
    UiPreferencesPatchSchema,
    UiPreferencesResponseSchema,
)
from app.core.user_preferences.service import user_ui_preferences_service
from app.core.access.schemas import UserProtocol

router = APIRouter(prefix="/user-preferences", tags=["user-preferences"])


@router.get("/", response_model=ApiResponse[UiPreferencesResponseSchema])
async def get_user_preferences(
    current_session: CurrentUser,
    db: DBSession,
) -> ApiResponse[UiPreferencesResponseSchema]:
    """Настройки интерфейса текущего пользователя."""
    data = await user_ui_preferences_service.get_for_user(
        db, user_id=typing_cast(UserProtocol, current_session).id
    )
    return ApiResponse(
        success=True, message="Настройки интерфейса получены", data=data
    )


@router.patch("/", response_model=ApiResponse[UiPreferencesResponseSchema])
async def patch_user_preferences(
    obj_in: UiPreferencesPatchSchema,
    current_session: CurrentUser,
    db: DBSession,
) -> ApiResponse[UiPreferencesResponseSchema]:
    """Частичное обновление настроек интерфейса текущего пользователя."""
    data = await user_ui_preferences_service.patch_for_user(
        db, user_id=typing_cast(UserProtocol, current_session).id, patch=obj_in
    )
    await db.commit()
    return ApiResponse(
        success=True, message="Настройки интерфейса сохранены", data=data
    )