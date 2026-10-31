"""Pydantic-схемы для реплики регионов в домене business_partners.

✅ Схемы включают полный контракт доступа для использования
   в AccessService и отображения в интерфейсе.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BpSalesRegionsReplicaResponseSchema(BaseModel):
    """Схема ответа: реплика региона из домена sales."""

    model_config = ConfigDict(from_attributes=True)

    region_id: uuid.UUID

    # Бизнес-данные
    name: str
    capital: str | None = None
    code: str | None = None
    area: str | None = None

    # ✅ Контракт доступа (§3.3)
    tenant_id: uuid.UUID
    section_id: uuid.UUID
    author_id: uuid.UUID
    or_tags: list[str] | None = None
    and_tags: list[str] | None = None

    # Метаданные синхронизации
    replica_version: int
    replica_synced_at: datetime
    is_deleted: bool


class BpSalesRegionsReplicaListItemSchema(BaseModel):
    """Минимальная схема для списков и справочников."""

    model_config = ConfigDict(from_attributes=True)

    region_id: uuid.UUID
    name: str
    code: str | None = None
    # ✅ Поле доступа для фильтрации в списках
    section_id: uuid.UUID


class BpSalesRegionsReplicaReferenceItemSchema(BaseModel):
    """
    Схема элемента для универсальных справочников фронтенда.
    Приводит region_id к имени id для совместимости с ReferenceSelect.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str