# backend/app/core/user_preferences/service.py
"""
Сервис персональных настроек интерфейса.
flush в сервисе, commit в роутере (Правило №31).
Атомарный merge под строковой блокировкой исключает потерю обновлений
при параллельных PATCH из разных вкладок/устройств.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from typing import cast as typing_cast

from app.core.user_preferences.models import UserUiPreferencesModel
from app.core.user_preferences.schemas import (
    JsonValue,
    TablePreferenceSchema,
    UiPreferencesPatchSchema,
    UiPreferencesResponseSchema,
    UiPreferencesSchema,
)


class UserUiPreferencesService:
    """Чтение и частичное обновление настроек текущего пользователя."""

    async def get_for_user(
        self, db: AsyncSession, *, user_id: uuid.UUID
    ) -> UiPreferencesResponseSchema:
        """Получить настройки; при отсутствии строки вернуть значения по умолчанию."""
        row = await self._get_row(db, user_id=user_id)
        return self._to_response(user_id=user_id, row=row)

    async def patch_for_user(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        patch: UiPreferencesPatchSchema,
    ) -> UiPreferencesResponseSchema:
        """Атомарно слить частичное обновление с текущим документом."""
        # Гарантируем существование строки без гонки на первом PATCH.
        await db.execute(
            pg_insert(UserUiPreferencesModel)
            .values(user_id=user_id, preferences={})
            .on_conflict_do_nothing(index_elements=["user_id"])
        )
        # Блокировка строки: конкурентные PATCH одного пользователя сериализуются.
        row = await self._get_row(db, user_id=user_id, lock=True)
        if row is None:
            # Недостижимо после upsert, но сохраняет строгую типизацию.
            row = UserUiPreferencesModel(user_id=user_id, preferences={})
            db.add(row)
            await db.flush()

        current = UiPreferencesSchema.model_validate(row.preferences)
        merged = self._merge(current=current, patch=patch)

        # typing_cast необходим: Pydantic model_dump возвращает dict[str, Any],
        # но содержимое гарантированно JSON-валидно после model_dump(mode="json").
        row.preferences = typing_cast(
            dict[str, JsonValue], merged.model_dump(mode="json")
        )
        await db.flush()
        await db.refresh(row)
        return self._to_response(user_id=user_id, row=row)

    async def _get_row(
        self, db: AsyncSession, *, user_id: uuid.UUID, lock: bool = False
    ) -> UserUiPreferencesModel | None:
        stmt = select(UserUiPreferencesModel).where(
            UserUiPreferencesModel.user_id == user_id
        )
        if lock:
            stmt = stmt.with_for_update()
        return (await db.execute(stmt)).scalar_one_or_none()

    @staticmethod
    def _merge(
        *, current: UiPreferencesSchema, patch: UiPreferencesPatchSchema
    ) -> UiPreferencesSchema:
        theme = patch.theme if patch.theme is not None else current.theme
        navigation = (
            patch.navigation if patch.navigation is not None else current.navigation
        )
        tables: dict[str, TablePreferenceSchema] = dict(current.tables)
        if patch.tables is not None:
            for key, value in patch.tables.items():
                if value is None:
                    tables.pop(key, None)
                else:
                    tables[key] = value
        return UiPreferencesSchema(
            theme=theme, navigation=navigation, tables=tables
        )

    @staticmethod
    def _to_response(
        *, user_id: uuid.UUID, row: UserUiPreferencesModel | None
    ) -> UiPreferencesResponseSchema:
        prefs = (
            UiPreferencesSchema.model_validate(row.preferences)
            if row is not None
            else UiPreferencesSchema()
        )
        return UiPreferencesResponseSchema(
            user_id=user_id,
            updated_at=row.updated_at if row is not None else None,
            theme=prefs.theme,
            navigation=prefs.navigation,
            tables=prefs.tables,
        )


user_ui_preferences_service = UserUiPreferencesService()