Изложи сразу все правила backend, но при этом каждое правило максимально подробно с примерами кода

Вот **максимально подробный и исчерпывающий** свод всех правил для **Backend** части проекта Cool ERP. Каждое правило раскрыто с указанием строгих требований, примеров правильного и неправильного кода, а также архитектурного обоснования.

---

# 📜 ПОЛНЫЙ СВОД ПРАВИЛ BACKEND (Cool ERP)

## Правило №1: Чистая архитектура и ORM (SQLAlchemy 2.0 + Pydantic)
**Суть:** Строгое разделение ответственности между слоем базы данных (SQLAlchemy) и слоем валидации/сериализации (Pydantic). Вычисляемые поля должны быть изолированы и безопасны.

**Строгие требования:**
1. Вычисляемые (derived) поля в моделях реализуются **только** через декоратор `@property`.
2. Связи `relationship` обязательно настраиваются с явным `back_populates` и `lazy="selectin"` (для предотвращения проблемы N+1 запросов при загрузке списков).
3. Во всех Pydantic-схемах, предназначенных для ответа клиенту (Response), обязательно наличие: `model_config = ConfigDict(from_attributes=True)`.

**✅ ПРАВИЛЬНО:**
```python
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pydantic import BaseModel, ConfigDict

class RoleModel(Base):
    __tablename__ = "roles"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    name: Mapped[str]
    
    # ✅ Явный back_populates и lazy="selectin"
    permissions = relationship("PermissionModel", back_populates="role", lazy="selectin")

    # ✅ Вычисляемое поле через @property
    @property
    def permissions_count(self) -> int:
        return len(self.permissions)

class RoleResponseSchema(BaseModel):
    id: uuid.UUID
    name: str
    permissions_count: int  # ✅ Pydantic автоматически прочитает это из @property
    
    # ✅ Обязательная конфигурация для чтения из ORM-объекта
    model_config = ConfigDict(from_attributes=True)
```

**❌ НЕПРАВИЛЬНО:**
```python
class RoleModel(Base):
    # ❌ Отсутствует back_populates и lazy="selectin" (будет N+1 или ленивая загрузка в цикле)
    permissions = relationship("PermissionModel")

class RoleResponseSchema(BaseModel):
    id: uuid.UUID
    name: str
    # ❌ Отсутствует model_config = ConfigDict(from_attributes=True)
    # Pydantic не сможет прочитать @property permissions_count
```

---

## Правило №4: Orval-совместимость API
**Суть:** Гарантированная типобезопасность на фронтенде через строгую, единообразную структуру ответов от всех списковых эндпоинтов.

**Строгие требования:**
Все эндпоинты, возвращающие коллекции данных, **обязаны** оборачивать результат в универсальную обёртку `ApiResponse[PaginatedResponse[T]]`, где `T` — это конкретная `ResponseSchema`.

**✅ ПРАВИЛЬНО:**
```python
from app.core.schemas import ApiResponse, PaginatedResponse
from app.core.roles.schemas import RoleResponseSchema

@router.get(
    "/", 
    response_model=ApiResponse[PaginatedResponse[RoleResponseSchema]] # ✅ Строгая типизация
)
async def get_roles(
    db: DBSession,
    skip: int = 0,
    limit: int = 100,
):
    items, total = await crud_role.get_multi(db, skip=skip, limit=limit)
    
    # ✅ Возврат строго через обёртки
    return ApiResponse(
        success=True,
        message="Роли успешно получены",
        data=PaginatedResponse(
            items=[RoleResponseSchema.model_validate(item) for item in items],
            total=total,
            page=(skip // limit) + 1,
            size=limit,
        )
    )
```

**❌ НЕПРАВИЛЬНО:**
```python
# ❌ Возврат "голого" списка или кортежа, который сломает генерацию типов Orval
@router.get("/", response_model=list[RoleResponseSchema])
async def get_roles(...):
    return items, total 
```

---

## Правило №21: Именование схем (Pydantic)
**Суть:** Предсказуемость, автодополнение в IDE и мгновенное понимание назначения схемы по её имени.

**Строгие требования:**
Все Pydantic-схемы должны иметь строгие суффиксы в зависимости от их назначения:
- `...CreateSchema`: для создания (все обязательные поля без `id`).
- `...UpdateSchema`: для обновления (поля часто `Optional`, `id` обычно передаётся в URL, а не в теле).
- `...ResponseSchema`: для ответов API (включает `id`, вычисляемые `@property` и денормализованные поля, такие как `tenant_name`).

**✅ ПРАВИЛЬНО:**
```python
class TenantCreateSchema(BaseModel):
    name: str
    description: str | None = None

class TenantUpdateSchema(BaseModel):
    name: str | None = None
    description: str | None = None

class TenantResponseSchema(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    is_active: bool
    model_config = ConfigDict(from_attributes=True)
```

---

## Правило №26: Multi-tenancy (Изоляция данных)
**Суть:** Жёсткая защита данных разных организаций (тенантов) на уровне SQL-запросов. Предотвращение утечек данных между клиентами.

**Строгие требования:**
1. В каждом методе CRUD (`get_multi`, `get`, `update`, `delete`) **обязательна** фильтрация по `tenant_id`.
2. Проверка: если `is_superadmin == False`, к SQL-запросу (`stmt`) добавляется `.where(Model.tenant_id == current_tenant_id)`.
3. Суперадмины (`is_superadmin == True`) видят все данные без фильтрации.
4. Фильтрация должна происходить **на уровне SQL** (через SQLAlchemy `where`), а не на уровне Python (не фильтровать список в памяти).

**✅ ПРАВИЛЬНО:**
```python
async def get_multi(
    self, db: AsyncSession, current_tenant_id: uuid.UUID, is_superadmin: bool, skip: int = 0, limit: int = 100
) -> tuple[list[RoleModel], int]:
    stmt = select(RoleModel)
    count_stmt = select(func.count()).select_from(RoleModel)

    # ✅ SQL-уровень: фильтрация только если не суперадмин
    if not is_superadmin and current_tenant_id:
        stmt = stmt.where(RoleModel.tenant_id == current_tenant_id)
        count_stmt = count_stmt.where(RoleModel.tenant_id == current_tenant_id)
    
    # ... выполнение запроса ...
```

**❌ НЕПРАВИЛЬНО:**
```python
async def get_multi(self, db: AsyncSession, current_tenant_id: uuid.UUID, is_superadmin: bool):
    stmt = select(RoleModel)
    result = await db.execute(stmt)
    items = result.scalars().all()
    
    # ❌ Фильтрация в памяти (Python-level): медленно и не масштабируется
    if not is_superadmin:
        items = [item for item in items if item.tenant_id == current_tenant_id]
```

---

## Правило №28: Схема БД и именованные ограничения
**Суть:** Явность при создании таблиц и избежание конфликтов имён при генерации или откате миграций.

**Строгие требования:**
1. В каждой модели SQLAlchemy в `__table_args__` должна быть явно указана схема: `{"schema": "public"}`.
2. Все `UniqueConstraint` (и другие ограничения) должны быть **именованными** (параметр `name="uq_..."`), чтобы облегчить чтение ошибок БД и управление миграциями.

**✅ ПРАВИЛЬНО:**
```python
from sqlalchemy import UniqueConstraint

class RoleModel(Base):
    __tablename__ = "roles"
    # ✅ Явное указание схемы и именованное ограничение уникальности
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_role_tenant_name"),
        {"schema": "public"}
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    tenant_id: Mapped[uuid.UUID]
    name: Mapped[str]
```

---

## Правило №30: M2M синхронизация и переиспользование моделей
**Суть:** Управление связями многие-ко-многим без "магии", которая ломает каскадные удаления или аудит. Избегание создания избыточных таблиц.

**Строгие требования:**
1. **Запрет на создание новых M2M-таблиц**, если в проекте уже есть подходящая полноценная модель (например, для полномочий ролей используется существующая `PermissionModel`, а не абстрактная связующая таблица `role_doctypes`).
2. Связи M2M синхронизируются в методах `create`/`update` либо через явные SQL-операции `insert` / `delete`, либо через ORM-механизмы с чётко определённым `cascade="all, delete-orphan"`.

**✅ ПРАВИЛЬНО:**
```python
class RoleModel(Base):
    __tablename__ = "roles"
    # ✅ Использование существующей модели PermissionModel с каскадным удалением
    permissions = relationship(
        "PermissionModel", 
        back_populates="role", 
        lazy="selectin", 
        cascade="all, delete-orphan"
    )
```

**❌ НЕПРАВИЛЬНО:**
```python
# ❌ Создание избыточной M2M таблицы, когда есть полноценная сущность Permission
role_doctypes = Table(
    "role_doctypes", Base.metadata,
    Column("role_id", ForeignKey("roles.id")),
    Column("doctype_id", ForeignKey("doctypes.id"))
)
```

---

## Правило №31: Приоритет CRUDBase
**Суть:** Единообразие слоя доступа к данным. Все CRUD-классы должны следовать единому контракту.

**Строгие требования:**
1. Все CRUD-классы **обязаны** наследоваться от базового `CRUDBase[Model, CreateSchema, UpdateSchema]`.
2. Переопределение методов (`get`, `create`, `update`, `delete`) допускается **только** при наличии специфичной бизнес-логики (например, проверка прав или M2M синхронизация).
3. **КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО** менять имена параметров переопределённых методов, если они совпадают с базовым классом. Стандартные имена: `obj_in`, `db_obj`, `is_superadmin`, `current_tenant_id`.

**✅ ПРАВИЛЬНО:**
```python
from app.core.crud.base import CRUDBase

class CRUDRole(CRUDBase[RoleModel, RoleCreateSchema, RoleUpdateSchema]):
    
    # ✅ Имена параметров соответствуют базовому классу
    async def update(
        self,
        db: AsyncSession,
        db_obj: RoleModel,
        obj_in: RoleUpdateSchema,
        current_tenant_id: uuid.UUID,
        is_superadmin: bool = False
    ) -> RoleModel:
        update_data = obj_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_obj, key, value)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

crud_role = CRUDRole()
```

**❌ НЕПРАВИЛЬНО:**
```python
class CRUDRole: # ❌ Не наследуется от CRUDBase
    async def update_role(self, db, role_id, data): # ❌ Нестандартные имена параметров
        pass
```

---

## Правило №32: Аннотированные типы зависимостей
**Суть:** Чистота сигнатур эндпоинтов, совместимость со статическим анализом и единый стиль внедрения зависимостей.

**Строгие требования:**
1. Запрещено использовать вызов `Depends(...)` напрямую в значениях аргументов по умолчанию в сигнатуре функции роутера.
2. Вместо этого используются строгие алиасы типов, определённые в `dependencies.py`: `SuperAdminUser`, `CurrentUser`, `DBSession`.

**✅ ПРАВИЛЬНО:**
```python
from app.core.auth.dependencies import DBSession, CurrentUser

@router.get("/")
async def get_roles(
    db: DBSession,          # ✅ Строгий алиас типа
    session: CurrentUser,   # ✅ Строгий алиас типа
    skip: int = 0,
):
    is_superadmin = session.is_superadmin
    # ...
```

**❌ НЕПРАВИЛЬНО:**
```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

@router.get("/")
async def get_roles(
    db: AsyncSession = Depends(get_db), # ❌ Запрещено использовать Depends в сигнатуре
    current_user = Depends(get_current_user), # ❌ Отсутствие строгой типизации
):
    pass
```

---

## Правило №33: Запрет присваивания в @property
**Суть:** Защита целостности вычисляемых полей и предотвращение ошибок ORM.

**Строгие требования:**
1. Поля, помеченные декоратором `@property` в моделях SQLAlchemy, являются **строго read-only**.
2. Прямое присваивание `item.field = value` для таких полей запрещено (это либо вызовет ошибку `AttributeError`, либо будет проигнорировано).
3. Pydantic автоматически считывает значения из `@property` при сериализации благодаря `model_config = ConfigDict(from_attributes=True)`.

**✅ ПРАВИЛЬНО:**
```python
class RoleModel(Base):
    @property
    def permissions_count(self) -> int:
        return len(self.permissions)

# В коде:
count = role.permissions_count # ✅ Чтение разрешено

# В Pydantic:
schema = RoleResponseSchema.model_validate(role) # ✅ Автоматически подхватит permissions_count
```

**❌ НЕПРАВИЛЬНО:**
```python
# ❌ Попытка записать значение в вычисляемое поле
role.permissions_count = 5 
```

---

## 📌 Зарезервированные номера правил Backend
Следующие номера зарезервированы для будущего расширения правил Backend и **не должны** переиспользоваться для других целей:
- **Правило №2**
- **Правило №3**
- **Правило №5**
- **Правило №6**
- **Правило №7**
- **Правило №8**

---

Этот документ является **единственным источником истины** для Backend-разработки в проекте Cool ERP. Любое отклонение от этих правил (например, использование `Depends` в сигнатуре или отсутствие `from_attributes=True`) будет считаться нарушением архитектуры и подлежит немедленному исправлению при код-ревью.