import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.tenants.models import TenantModel


class SectionType:
    """Типы разделов (ТЗ §4.1)."""

    PLATFORM: str = "platform"              # Общий платформенный
    TENANT_DEFAULT: str = "tenant_default"  # Общий для организации
    CUSTOM: str = "custom"                  # Произвольный


# ✅ Множество защищённых типов (нельзя удалить или переименовать)
PROTECTED_SECTION_TYPES: frozenset[str] = frozenset({
    SectionType.PLATFORM,
    SectionType.TENANT_DEFAULT,
})


class SectionModel(Base):
    """
    Разделы — логические пространства доступа (ТЗ §4).

    Типы разделов:
    - platform:       общий платформенный (виден всем организациям, удалить нельзя)
    - tenant_default: общий для организации (создаётся автоматически, удалить нельзя)
    - custom:         произвольный (создаётся администратором)

    Правило ТЗ §3.2.1: Раздел — логический механизм доступа,
    не связан с физическим хранением.
    """

    # ✅ Явная типизация атрибутов класса
    # __tablename__: str = "sections"
    # __table_args__: ClassVar[tuple[UniqueConstraint, dict[str, str]]] = (
    #     UniqueConstraint("tenant_id", "name", name="uq_section_tenant_name"),
    #     {"schema": "public"},
    # )
    __tablename__ = "sections"
    __table_args__ = (
        # ✅ Правило №28: именованное ограничение уникальности
        UniqueConstraint("tenant_id", "name", name="uq_section_tenant_name"),
        {"schema": "public"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuid_generate_v4()"),
    )
    # ✅ NULL для платформенных разделов (видны всем организациям)
    # ✅ ForeignKey добавлен — без него SQLAlchemy не может определить
    # join condition для relationship TenantModel.sections
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.tenants.id"),
        nullable=True,
        index=True,
        comment="NULL для платформенных разделов",
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ✅ Тип раздела: platform | tenant_default | custom
    section_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=SectionType.CUSTOM,
        server_default=text("'custom'"),
        comment="Тип раздела: platform | tenant_default | custom",
    )

    # Аудит времени и «кто» (ТЗ §12.2)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    # ✅ Правило №42: связь для денормализации
    # ✅ Обратная связь к TenantModel.
    # Объявляется симметрично TenantModel.sections (back_populates="tenant").
    # Тип TenantModel | None, так как tenant_id nullable
    # (для платформенных разделов тенант отсутствует).
    tenant: Mapped["TenantModel | None"] = relationship(
        "TenantModel",
        back_populates="sections",
        lazy="selectin",
    )

    # ✅ Правило №1 / №33: вычисляемые поля только через @property

    # ✅ Правило №42: @property для денормализации
    @property
    def tenant_name(self) -> str | None:
        """Название организации для ReferenceSelect и списков."""
        return self.tenant.name if self.tenant else None
    
    @property
    def is_protected(self) -> bool:
        """Раздел защищён от удаления и переименования."""
        return self.section_type in PROTECTED_SECTION_TYPES

    @property
    def section_type_label(self) -> str:
        """Человекочитаемое имя типа раздела."""
        labels: dict[str, str] = {
            SectionType.PLATFORM: "Общий (платформенный)",
            SectionType.TENANT_DEFAULT: "Общий для организации",
            SectionType.CUSTOM: "Произвольный",
        }
        return labels.get(self.section_type, self.section_type)