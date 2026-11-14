from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AccessAuditCreate(BaseModel):
    tenant_id: UUID
    user_id: UUID | None = None
    action: str
    resource: str
    status: str
    ip_address: str | None = None


class AuditAccessRead(BaseModel):
    id: UUID
    tenant_id: UUID
    user_id: UUID | None = None
    user_email: str | None = None
    action: str
    resource: str
    status: str
    ip_address: str | None = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AuditDataRead(BaseModel):
    id: UUID
    tenant_id: UUID
    user_id: UUID | None = None
    user_email: str | None = None
    entity_type: str
    entity_id: UUID
    entity_name: str | None = None
    action: str
    changes: dict[str, Any] | None = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class DataAuditCreate(BaseModel):
    tenant_id: UUID
    user_id: UUID | None = None
    entity_type: str
    entity_id: UUID
    entity_name: str | None = None
    action: str
    changes: dict[str, Any] | None = None


class AuditFilter(BaseModel):
    entity_type: str | None = None
    entity_id: UUID | None = None
    action: str | None = None