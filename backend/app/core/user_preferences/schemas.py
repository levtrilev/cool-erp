# backend/app/core/user_preferences/schemas.py
"""Схемы персональных настроек интерфейса (UI preferences)."""
import re
import uuid
from datetime import datetime
from typing import Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Рекурсивный JSON-тип для JSONB без Any (Правило №44).
JsonPrimitive: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonPrimitive | list["JsonValue"] | dict[str, "JsonValue"]

ThemeMode: TypeAlias = Literal["light", "dark", "system"]
NavigationLayout: TypeAlias = Literal["sidebar", "topbar"]
SortDirection: TypeAlias = Literal["asc", "desc"]

# Идентификатор палитры — строка, а не Literal:
# каталог палитр задан на фронтенде (theme-context.ts) и расширяется там.
# Бэкенд ограничивает формат и длину, не дублируя список значений.
# Неизвестный id фронтенд нормализует в "default" при чтении.
_PALETTE_ID_PATTERN = r"^[a-z0-9][a-z0-9_-]{0,31}$"

_KEY_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
_MAX_TABLES = 100
_MAX_COLUMNS = 100


def _validate_keys(keys: list[str], label: str, limit: int) -> None:
    if len(keys) > limit:
        raise ValueError(f"Слишком много элементов в {label}: максимум {limit}")
    for key in keys:
        if not _KEY_PATTERN.fullmatch(key):
            raise ValueError(f"Недопустимый ключ {label}: {key}")


class ThemePreferenceSchema(BaseModel):
    """
    Тема интерфейса: режим и палитра для каждой из двух тем.
    Палитры хранятся раздельно, поэтому переключение light/dark
    не сбрасывает выбранный вариант оформления.
    """

    mode: ThemeMode = "system"
    light_palette: str = Field(
        default="default", max_length=32, pattern=_PALETTE_ID_PATTERN
    )
    dark_palette: str = Field(
        default="default", max_length=32, pattern=_PALETTE_ID_PATTERN
    )


class NavigationPreferenceSchema(BaseModel):
    """Раскладка и состояние навигации."""

    layout: NavigationLayout = "sidebar"
    sidebar_collapsed: bool = False


class TableColumnStateSchema(BaseModel):
    """Сортировка и фильтр одной колонки."""

    sort: SortDirection | None = None
    filter: str | None = Field(default=None, max_length=512)


class TablePreferenceSchema(BaseModel):
    """Настройки одной таблицы: колонки, поиск, пагинация."""

    column_states: dict[str, TableColumnStateSchema] = Field(default_factory=dict)
    search: str = Field(default="", max_length=512)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=15, ge=1, le=200)

    @field_validator("column_states")
    @classmethod
    def validate_column_keys(
        cls, value: dict[str, TableColumnStateSchema]
    ) -> dict[str, TableColumnStateSchema]:
        _validate_keys(list(value.keys()), "column_states", _MAX_COLUMNS)
        return value


class UiPreferencesSchema(BaseModel):
    """Полный документ настроек интерфейса."""

    theme: ThemePreferenceSchema = Field(default_factory=ThemePreferenceSchema)
    navigation: NavigationPreferenceSchema = Field(
        default_factory=NavigationPreferenceSchema
    )
    tables: dict[str, TablePreferenceSchema] = Field(default_factory=dict)

    @field_validator("tables")
    @classmethod
    def validate_table_keys(
        cls, value: dict[str, TablePreferenceSchema]
    ) -> dict[str, TablePreferenceSchema]:
        _validate_keys(list(value.keys()), "tables", _MAX_TABLES)
        return value


class UiPreferencesPatchSchema(BaseModel):
    """
    Частичное обновление.
    theme/navigation заменяются целиком — клиент всегда присылает
    полный объект секции (см. toApiThemePreference на фронтенде);
    tables обновляется по ключам (null удаляет настройки таблицы).
    """

    theme: ThemePreferenceSchema | None = None
    navigation: NavigationPreferenceSchema | None = None
    tables: dict[str, TablePreferenceSchema | None] | None = None

    @field_validator("tables")
    @classmethod
    def validate_patch_table_keys(
        cls, value: dict[str, TablePreferenceSchema | None] | None
    ) -> dict[str, TablePreferenceSchema | None] | None:
        if value is not None:
            _validate_keys(list(value.keys()), "tables", _MAX_TABLES)
        return value


class UiPreferencesResponseSchema(UiPreferencesSchema):
    """Ответ API: документ + служебные поля."""

    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    updated_at: datetime | None = None