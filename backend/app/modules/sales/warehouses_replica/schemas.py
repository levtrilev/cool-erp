"""Pydantic-схемы для реплики складов в домене sales.

Реплика доступна только для чтения.
Запись выполняется репликатором (см. handlers.py).
Поэтому схемы Create/Update отсутствуют (Правило №21 — только Response).
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SalesInvWarehousesReplicaResponseSchema(BaseModel):
    """
    Полная схема ответа: реплика склада из домена inventory.

    Используется для отображения данных реплики в интерфейсе
    и для отладки синхронизации.
    """

    # ✅ Правило №1: чтение из ORM-атрибутов
    model_config = ConfigDict(from_attributes=True)

    # ID оригинала из домена inventory
    warehouse_id: uuid.UUID

    # Скопированные данные
    name: str
    description: str | None = None
    tenant_id: uuid.UUID

    # Метаданные синхронизации
    replica_version: int
    replica_synced_at: datetime
    is_deleted: bool


class SalesInvWarehousesReplicaListItemSchema(BaseModel):
    """
    Минимальная схема для списков и справочников.

    Используется в ReferenceSelect / ReferenceMultiSelectChips,
    где нужны только идентификатор и название.
    """

    model_config = ConfigDict(from_attributes=True)

    warehouse_id: uuid.UUID
    name: str
    description: str | None = None


class SalesInvWarehousesReferenceItemSchema(BaseModel):
    """
    Схема элемента для универсальных справочников фронтенда.

    Приводит warehouse_id к имени id, чтобы реплика была
    совместима с ReferenceSelect (ReferenceItem: { id, name }).
    """

    model_config = ConfigDict(from_attributes=True)

    # ✅ Поле id формируется из warehouse_id в CRUD-методе
    id: str
    name: str