# Правило №1: Чистая архитектура (ПРИОРИТЕТ)

При работе со связанными данными **ОБЯЗАТЕЛЬНО** использовать полный стек технологий SQLAlchemy + Pydantic для автоматической конвертации между слоями приложения. Ручное создание словарей для передачи данных между слоями **КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО**.

**ОБЯЗАТЕЛЬНЫЙ СТЕК:**
* SQLAlchemy `relationship` с `back_populates` и `lazy="selectin"` в моделях
* `@property` в ORM-модели для вычисляемых полей (например, `user.tenant_name`)
* `from_attributes=True` в Pydantic-схемах (через `model_config = ConfigDict(from_attributes=True)`)
* Автоматическая конвертация через `ModelSchema.model_validate(orm_object)`

---

### 1. Обоснование (Почему это критически важно)

1. **Разделение слоёв (Separation of Concerns):** Приложение состоит из трёх чётко разделённых слоёв:
   * **Слой данных (ORM):** SQLAlchemy модели, которые маппятся на таблицы PostgreSQL.
   * **Слой DTO (Data Transfer Object):** Pydantic-схемы, которые определяют контракт API.
   * **Слой транспорта (HTTP):** FastAPI роутеры, которые принимают запросы и возвращают ответы.
   
   Каждый слой работает со своими объектами. ORM-модель не должна «просачиваться» в API-ответ, а Pydantic-схема не должна использоваться для запросов к БД.

2. **Безопасность данных:** Явная конвертация через `.model_validate()` гарантирует, что в API-ответ попадут **только** те поля, которые объявлены в Pydantic-схеме. Случайно «протащить» секретное поле (например, `hashed_password`) невозможно.

3. **Производительность:** `lazy="selectin"` загружает связанные данные одним SQL-запросом (JOIN), а не N+1 запросами. Это критически важно для списковых эндпоинтов.

4. **Типобезопасность:** Pydantic v2 с `from_attributes=True` автоматически проверяет типы данных при конвертации из ORM-объекта. Если в БД хранится `None`, а схема ожидает `str`, вы получите ошибку валидации на этапе разработки, а не баг в production.

5. **Orval-совместимость:** Orval генерирует TypeScript-типы на основе Pydantic-схем. Если данные возвращаются через ручные словари, OpenAPI-спецификация будет некорректной, и фронтенд потеряет типобезопасность.

6. **Поддерживаемость:** Когда вся конвертация централизована в одном месте (`.model_validate()`), добавление нового поля требует изменения только в трёх местах: модель, схема, миграция. Не нужно искать все ручные словари по коду.

---

### 2. Обязательные требования к реализации

#### 2.1. SQLAlchemy `relationship` с `back_populates`
Все связи между таблицами **ОБЯЗАТЕЛЬНО** должны быть объявлены через `relationship` с явным указанием `back_populates` на обеих сторонах связи. Это создаёт двунаправленную навигацию между объектами.

#### 2.2. Стратегия загрузки `lazy="selectin"`
Для связей, которые **всегда** нужны при чтении (например, `tenant` для `role`), **ОБЯЗАТЕЛЬНО** использовать `lazy="selectin"`. Это загружает связанные данные одним SQL-запросом с `IN (...)`.

Для связей, которые нужны **редко** (например, все `roles` для `tenant` при удалении), допустимо использовать `lazy="joined"` или явную загрузку через `selectinload`.

#### 2.3. Вычисляемые поля через `@property`
Если в API-ответе нужно поле, которого нет в таблице БД (например, `tenant_name` — имя организации, связанной с пользователем), **ОБЯЗАТЕЛЬНО** использовать `@property` в ORM-модели, а не ручное добавление поля в словаре.

#### 2.4. `from_attributes=True` в Pydantic-схемах
Все Pydantic-схемы, которые используются для конвертации из ORM-объектов (обычно `ResponseSchema`), **ОБЯЗАТЕЛЬНО** должны иметь:
```python
model_config = ConfigDict(from_attributes=True)
```
Это позволяет Pydantic читать атрибуты ORM-объекта так же, как атрибуты словаря.

#### 2.5. Явная конвертация через `.model_validate()`
В роутерах и сервисах **ОБЯЗАТЕЛЬНО** использовать `.model_validate()` для конвертации ORM-объекта в Pydantic-схему:
```python
RoleResponseSchema.model_validate(role_orm_object)
```

---

### 3. Примеры кода

#### ✅ ПРАВИЛЬНО: Полный стек чистой архитектуры

**Шаг 1. ORM-модель (`models.py`):**
```python
# backend/app/core/roles/models.py
import uuid
from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class RoleModel(Base):
    __tablename__ = "roles"
    __table_args__ = {"schema": "public"}  # ✅ Правило №28

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.tenants.id", ondelete="CASCADE"),  # ✅ Правило №28
        nullable=False,
    )

    # ✅ Связь с тенантом: selectin для автоматической загрузки
    tenant = relationship("TenantModel", lazy="selectin")

    # ✅ Связь с полномочиями: back_populates для двунаправленности
    permissions = relationship(
        "PermissionModel",
        back_populates="role",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    # ✅ Вычисляемое поле через @property
    @property
    def tenant_name(self) -> str | None:
        """Имя организации, к которой принадлежит роль."""
        return self.tenant.name if self.tenant else None
```

**Шаг 2. Pydantic-схема (`schemas.py`):**
```python
# backend/app/core/roles/schemas.py
import uuid
from typing import Optional
from pydantic import BaseModel, ConfigDict


class RoleBaseSchema(BaseModel):
    name: str
    description: str | None = None


class RoleCreateSchema(RoleBaseSchema):
    tenant_id: uuid.UUID


class RoleUpdateSchema(BaseModel):
    name: str | None = None
    description: str | None = None


class RoleResponseSchema(RoleBaseSchema):
    # ✅ КРИТИЧЕСКИ ВАЖНО: Разрешаем чтение из ORM-атрибутов
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    tenant_id: uuid.UUID
    
    # ✅ Вычисляемое поле — Pydantic прочитает его из @property ORM-модели
    tenant_name: Optional[str] = None
    
    # ✅ Вложенные объекты — Pydantic автоматически сконвертирует relationship
    permissions: list["PermissionResponseSchema"] = []
```

**Шаг 3. Роутер (`router.py`):**
```python
# backend/app/core/roles/router.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import cast

from app.core.database import get_db
from app.core.auth.dependencies import get_current_session
from app.core.roles.crud import crud_role
from app.core.roles.schemas import RoleResponseSchema
from app.core.schemas import ApiResponse, PaginatedResponse

router = APIRouter(prefix="/roles", tags=["Roles"])


@router.get("/", response_model=ApiResponse[PaginatedResponse[RoleResponseSchema]])
async def get_roles(
    skip: int = 0,
    limit: int = 10,
    search: str | None = None,
    current_session=Depends(get_current_session),
    db: AsyncSession = Depends(get_db),
):
    # 1. Получаем ORM-объекты из CRUD
    items, total = await crud_role.get_multi_paginated(
        db,
        skip=skip,
        limit=limit,
        search=search,
        current_tenant_id=current_session.tenant_id,
        is_superadmin=current_session.is_superadmin,
    )
    
    # 2. ✅ АВТОМАТИЧЕСКАЯ КОНВЕРТАЦИЯ ORM → Pydantic
    # Pydantic сам прочитает:
    #   - role.id, role.name, role.description (из колонок)
    #   - role.tenant_name (из @property)
    #   - role.permissions (из relationship с lazy="selectin")
    paginated_data = cast(
        PaginatedResponse[RoleResponseSchema],
        PaginatedResponse(
            items=[RoleResponseSchema.model_validate(item) for item in items],
            total=total,
            skip=skip,
            limit=limit,
        )
    )
    
    # 3. ✅ Обёртка в ApiResponse (Правило №4)
    return ApiResponse(
        success=True,
        message="Роли получены",
        data=paginated_data,
    )
```

#### ✅ ПРАВИЛЬНО: Двунаправленная связь (back_populates)

**Модель роли:**
```python
class RoleModel(Base):
    __tablename__ = "roles"
    __table_args__ = {"schema": "public"}
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("public.tenants.id"), nullable=False
    )
    
    # ✅ Связь "вперёд": роль → тенант
    tenant = relationship("TenantModel", back_populates="roles", lazy="selectin")
```

**Модель тенанта:**
```python
class TenantModel(Base):
    __tablename__ = "tenants"
    __table_args__ = {"schema": "public"}
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    
    # ✅ Связь "назад": тенант → роли (back_populates указывает на RoleModel.tenant)
    roles = relationship("RoleModel", back_populates="tenant", lazy="selectin")
```

#### ✅ ПРАВИЛЬНО: Вычисляемое поле через @property

```python
class UserModel(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "public"}
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    first_name: Mapped[str] = mapped_column(Text, nullable=False)
    last_name: Mapped[str] = mapped_column(Text, nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("public.tenants.id"), nullable=False
    )
    
    tenant = relationship("TenantModel", lazy="selectin")
    
    # ✅ Вычисляемые поля — НЕ хранятся в БД, но доступны как атрибуты
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
    
    @property
    def tenant_name(self) -> str | None:
        return self.tenant.name if self.tenant else None
```

**Схема ответа:**
```python
class UserResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    first_name: str
    last_name: str
    
    # ✅ Pydantic автоматически прочитает @property из ORM-модели
    full_name: str
    tenant_name: str | None = None
```

#### ❌ НЕПРАВИЛЬНО: Ручные словари (Антипаттерн)

```python
# ❌ ГРУБОЕ НАРУШЕНИЕ ПРАВИЛА №1
@router.get("/", response_model=list[dict])
async def get_roles(db: AsyncSession = Depends(get_db)):
    roles = await db.execute(select(RoleModel))
    
    # ❌ РУЧНОЙ СЛОВАРЬ — ЗАПРЕЩЕНО!
    return [
        {
            "id": str(role.id),
            "name": role.name,
            "description": role.description,
            "tenant_name": role.tenant.name if role.tenant else None,  # ❌ Ручной доступ
            "permissions": [
                {
                    "id": str(p.id),
                    "doctype": p.doctype,
                    "full_access": p.full_access,
                }
                for p in role.permissions  # ❌ Может вызвать N+1 запрос!
            ],
        }
        for role in roles.scalars().all()
    ]
```
*Почему это катастрофически плохо:*
1. **Утечка данных:** Легко случайно добавить `role.hashed_password` в словарь.
2. **N+1 запросы:** Если `lazy="select"` (по умолчанию), доступ к `role.permissions` вызовет отдельный SQL-запрос для каждой роли. При 100 ролях — 101 запрос к БД.
3. **Нет валидации:** Если `role.name` окажется `None` (баг в БД), словарь вернёт `None`, а фронтенд упадёт.
4. **Нет типобезопасности:** Orval не сможет сгенерировать типы для `list[dict]`.
5. **Дублирование кода:** При добавлении поля `tenant_name` придётся искать все ручные словари по коду.

#### ❌ НЕПРАВИЛЬНО: Возврат ORM-объекта напрямую

```python
# ❌ ОШИБКА: ORM-объект без конвертации
@router.get("/{role_id}")
async def get_role(role_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    role = await db.get(RoleModel, role_id)
    return role  # ❌ FastAPI попытается сериализовать ORM-объект напрямую
```
*Почему это плохо:*
1. FastAPI не знает, как сериализовать `datetime`, `UUID`, `relationship` в JSON без настройки.
2. В ответ попадут **все** поля ORM-модели, включая секретные.
3. OpenAPI-спецификация будет некорректной.

#### ❌ НЕПРАВИЛЬНО: Отсутствие `from_attributes=True`

```python
# ❌ ОШИБКА: Схема без from_attributes
class RoleResponseSchema(BaseModel):
    id: uuid.UUID
    name: str
    # ❌ Нет model_config = ConfigDict(from_attributes=True)

# В роутере:
role = await db.get(RoleModel, role_id)
return RoleResponseSchema.model_validate(role)  
# 💥 ValidationError: Pydantic ожидает словарь, а получил ORM-объект
```
*Почему это плохо:* Без `from_attributes=True` Pydantic v2 не умеет читать атрибуты ORM-объекта. Он ожидает словарь (`dict`), а получает объект с атрибутами. Результат — ошибка валидации.

#### ❌ НЕПРАВИЛЬНО: Отсутствие `lazy="selectin"`

```python
# ❌ ОШИБКА: Связь без стратегии загрузки
class RoleModel(Base):
    tenant = relationship("TenantModel")  # ❌ lazy="select" по умолчанию
    
    permissions = relationship("PermissionModel")  # ❌ N+1 при доступе
```
*Почему это плохо:* При загрузке 10 ролей и обращении к `role.tenant_name` для каждой, SQLAlchemy выполнит 10 дополнительных запросов `SELECT * FROM tenants WHERE id = ...`. С `lazy="selectin"` это будет один запрос: `SELECT * FROM tenants WHERE id IN (...)`.

---

### 4. Нюансы и лучшие практики

#### 4.1. Стратегии загрузки SQLAlchemy

| Стратегия | SQL-запросы | Когда использовать |
| :--- | :--- | :--- |
| `lazy="select"` (по умолчанию) | N+1 | ❌ Избегать в API |
| `lazy="selectin"` | 2 (основной + IN) | ✅ Для связей, которые всегда нужны |
| `lazy="joined"` | 1 (JOIN) | ✅ Для связей "один-к-одному" |
| `lazy="subquery"` | 2 (основной + подзапрос) | ⚠️ Для больших коллекций |
| `lazy="noload"` | 1 (без связи) | ✅ Когда связь точно не нужна |
| `lazy="raise"` | Ошибка | ✅ Для отладки N+1 |

**Рекомендация для Cool ERP:** Используйте `lazy="selectin"` для всех связей, которые отображаются в API-ответах. Это оптимальный баланс между производительностью и простотой.

#### 4.2. Вложенные объекты в схемах
Pydantic v2 автоматически конвертирует вложенные `relationship`, если в схеме объявлен соответствующий тип:

```python
class RoleResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    name: str
    
    # ✅ Pydantic автоматически сконвертирует role.permissions
    # (список PermissionModel → список PermissionResponseSchema)
    permissions: list["PermissionResponseSchema"] = []


class PermissionResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    doctype: str
    full_access: bool
```

#### 4.3. Циклические импорты
При вложенных схемах могут возникнуть циклические импорты. Решения:
1. Использовать строковые аннотации (`"PermissionResponseSchema"`) и `model_rebuild()`.
2. Вынести общие схемы в отдельный файл.
3. Использовать `TYPE_CHECKING` для импортов типов.

```python
from __future__ import annotations  # ✅ Решает большинство проблем

class RoleResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    permissions: list[PermissionResponseSchema] = []  # ✅ Работает с __future__
```

#### 4.4. Исключение полей из ответа
Если нужно исключить поле из API-ответа (например, `tenant_id` для публичных эндпоинтов), используйте `exclude` в `model_dump()` или просто не объявляйте его в схеме:

```python
class RolePublicSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    name: str
    # ✅ tenant_id НЕ объявлен — не попадёт в ответ
```

#### 4.5. Связь с Правилом №4 (Orval-совместимость)
Чистая архитектура — это фундамент Orval-совместимости. Когда роутер возвращает `RoleResponseSchema.model_validate(role)`, FastAPI автоматически генерирует корректную OpenAPI-спецификацию, которую Orval использует для генерации TypeScript-типов.

#### 4.6. Связь с Правилом №26 (Безопасность multi-tenancy)
`@property` в ORM-модели и `from_attributes=True` в Pydantic не заменяют фильтрацию по `tenant_id`. Они лишь обеспечивают корректную конвертацию данных **после** того, как безопасность уже обеспечена на уровне CRUD.

#### 4.7. Связь с Правилом №30 (Sync Pattern)
При синхронизации подчиненных объектов (например, полномочий роли) чистая архитектура гарантирует, что каждый подчиненный объект корректно конвертируется из ORM в Pydantic и обратно.

---

### 5. Типичные ошибки и их исправление

| Ошибка | Исправление |
| :--- | :--- |
| Ручной словарь `{"id": role.id, ...}` | `RoleResponseSchema.model_validate(role)` |
| Возврат ORM-объекта напрямую | Конвертация через `.model_validate()` |
| Отсутствие `from_attributes=True` | Добавить `model_config = ConfigDict(from_attributes=True)` |
| Отсутствие `lazy="selectin"` | Добавить `lazy="selectin"` в `relationship` |
| Отсутствие `back_populates` | Добавить на обеих сторонах связи |
| N+1 запросы в цикле | Использовать `selectin` или `joined` загрузку |
| Ручное добавление `tenant_name` в словаре | `@property` в ORM + поле в Pydantic-схеме |
| Утечка `hashed_password` в ответ | Не объявлять поле в `ResponseSchema` |

---

### 6. Чек-лист для разработчика

При создании нового домена или рефакторинге существующего проверьте:

**ORM-модели (`models.py`):**
- [ ] Все связи объявлены через `relationship`?
- [ ] Используется ли `back_populates` на обеих сторонах связи?
- [ ] Указана ли стратегия `lazy="selectin"` для связей, отображаемых в API?
- [ ] Вычисляемые поля реализованы через `@property`?
- [ ] Указана ли схема `public` в `__table_args__` (Правило №28)?
- [ ] Все `ForeignKey` содержат префикс `public.` (Правило №28)?

**Pydantic-схемы (`schemas.py`):**
- [ ] Все `ResponseSchema` имеют `model_config = ConfigDict(from_attributes=True)`?
- [ ] Вычисляемые поля объявлены в схеме (соответствуют `@property` в модели)?
- [ ] Вложенные объекты (relationship) объявлены в схеме с правильным типом?
- [ ] Секретные поля (`hashed_password`, `token`) **НЕ** объявлены в `ResponseSchema`?
- [ ] Все схемы имеют суффикс `Schema` (Правило №21)?

**Роутеры (`router.py`):**
- [ ] Используется ли `.model_validate()` для конвертации ORM → Pydantic?
- [ ] Отсутствуют ли ручные словари `{"id": obj.id, ...}`?
- [ ] Отсутствует ли возврат ORM-объектов напрямую?
- [ ] Указан ли `response_model` в декораторе роутера?
- [ ] Используется ли `ApiResponse` и `PaginatedResponse` (Правило №4)?

**Производительность:**
- [ ] Нет ли N+1 запросов при загрузке списков?
- [ ] Используется ли `selectin` для связей, которые всегда нужны?
- [ ] Проверена ли производительность через SQL-логи (`echo=True` в engine)?

**Безопасность:**
- [ ] Не попадают ли секретные поля в API-ответ?
- [ ] Применяется ли фильтрация по `tenant_id` (Правило №26)?

---

### 7. Визуальная схема потока данных

```
┌─────────────┐      ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Клиент    │────▶│   Роутер    │────▶│    CRUD     │────▶│  PostgreSQL │
│  (React)    │◀────│  (FastAPI)  │◀────│ (SQLAlchemy)│◀────│   (БД)      │
└─────────────┘      └─────────────┘     └─────────────┘     └─────────────┘
                           │                    │
                           │                    │ ORM-объект
                           │                    │ (RoleModel)
                           │                    ▼
                           │            ┌─────────────┐
                           │            │  @property  │
                           │            │ tenant_name │
                           │            └─────────────┘
                           │                    │
                           │                    ▼
                           │            ┌─────────────┐
                           │            │ .model_     │
                           │            │ validate()  │
                           │            └─────────────┘
                           │                    │
                           │                    │ Pydantic-объект
                           │                    │ (RoleResponseSchema)
                           ▼                    ▼
                    ┌─────────────┐
                    │ ApiResponse │
                    │ {success,   │
                    │  message,   │
                    │  data}      │
                    └─────────────┘
                           │
                           │ JSON
                           ▼
                    ┌─────────────┐
                    │   Клиент    │
                    │ (Orval хук) │
                    └─────────────┘
```

---

Следование этому правилу гарантирует, что архитектура Cool ERP будет:
✅ **Безопасной** — секретные поля никогда не попадут в API-ответ
✅ **Производительной** — нет N+1 запросов, оптимальная загрузка связей
✅ **Типобезопасной** — от PostgreSQL до TypeScript через Pydantic и Orval
✅ **Поддерживаемой** — добавление поля требует изменения в 3 местах, а не в 30
✅ **Масштабируемой** — единый паттерн для всех доменов

Это правило является **фундаментом** всей архитектуры проекта и работает в связке с абсолютно всеми остальными правилами: №2 (CRUD), №4 (Orval), №21 (Схемы), №26 (Безопасность), №28 (Схема `public`), №30 (Sync Pattern).