"""Pydantic-схемы для реплики товаров в домене inventory."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class InvSalesGoodsReplicaResponseSchema(BaseModel):
    """Схема ответа: реплика товара из домена sales."""

    model_config = ConfigDict(from_attributes=True)

    goods_id: uuid.UUID
    name: str
    description: str | None = None
    tenant_id: uuid.UUID
    replica_version: int
    replica_synced_at: datetime
    is_deleted: bool


class InvSalesGoodsReplicaListItemSchema(BaseModel):
    """Схема для списков (минимальный набор полей)."""

    model_config = ConfigDict(from_attributes=True)

    goods_id: uuid.UUID
    name: str
    description: str | None = None