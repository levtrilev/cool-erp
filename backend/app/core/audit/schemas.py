from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

class AccessAuditCreate(BaseModel):
    tenant_id: UUID
    user_id: Optional[UUID] = None
    action: str
    resource: str
    status: str
    ip_address: Optional[str] = None

class AuditAccessRead(BaseModel):
    id: UUID
    tenant_id: UUID
    user_id: Optional[UUID] = None
    user_email: Optional[str] = None
    action: str
    resource: str
    status: str
    ip_address: Optional[str] = None
    created_at: datetime
    model_config = {"from_attributes": True}

class AuditDataRead(BaseModel):
    id: UUID
    tenant_id: UUID
    user_id: Optional[UUID] = None
    user_email: Optional[str] = None
    entity_type: str
    entity_id: UUID
    entity_name: Optional[str] = None
    action: str
    changes: Optional[dict] = None
    created_at: datetime
    model_config = {"from_attributes": True}

class DataAuditCreate(BaseModel):
    tenant_id: UUID
    user_id: Optional[UUID] = None
    entity_type: str
    entity_id: UUID
    entity_name: Optional[str] = None
    action: str
    changes: Optional[dict] = None


class AuditFilter(BaseModel):
    entity_type: Optional[str] = None
    entity_id: Optional[UUID] = None
    action: Optional[str] = None