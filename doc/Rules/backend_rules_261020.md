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

## Правило №40: Требования к Backend для корректной работы блокировок редактирования документов

**Суть:** Любой тип документа, наследующий `DocumentLifecycleMixin`, обязан реализовывать **двухуровневую систему блокировок** — оптимистическую (поле `version`) и пессимистическую (поля `editing_by_user_id` + `editing_since`). Оба механизма должны быть согласованы между собой на уровне CRUD-методов и роутера. Нарушение любого из требований приводит либо к потере данных (перезапись чужих изменений), либо к невозможности редактирования (вечная блокировка), либо к ложному ощущению безопасности (пользователь редактирует, не зная, что документ занят).

Правило обязательно для всех модулей, реализующих контракт документов (ТЗ §3.3 + жизненный цикл). Эталонная реализация — модуль `notes`.

---

### Часть 1. Требования к модели (наследник `DocumentLifecycleMixin`)

#### 1.1. Обязательные поля

Миксин `DocumentLifecycleMixin` уже содержит все необходимые поля. Наследник **не должен** переопределять или дублировать их:

| Поле | Тип | Назначение |
|------|-----|------------|
| `version` | `Integer NOT NULL DEFAULT 1` | Оптимистическая блокировка |
| `editing_by_user_id` | `UUID NULL FK → users.id` | Пессимистическая блокировка: кто редактирует |
| `editing_since` | `DateTime(timezone=True) NULL` | Пессимистическая блокировка: когда начал |

#### 1.2. Обязательное вычисляемое поле `is_editing_locked`

Каждый наследник `DocumentLifecycleMixin` обязан реализовать `@property is_editing_locked` для сериализации в `ResponseSchema`. Это поле использует фронтенд для отображения иконки замка и принятия решения о вызове `/lock`.

✅ **ПРАВИЛЬНО:**
```python
from datetime import datetime, timedelta, timezone
from app.core.doctypes.document_base import EDITING_LOCK_TIMEOUT_MINUTES

class NotesModel(DocumentAccessMixin, DocumentLifecycleMixin, Base):
    # ... специфичные поля ...

    # ✅ Правило №33: @property только для чтения, без присваиваний
    @property
    def is_editing_locked(self) -> bool:
        """Активна ли пессимистическая блокировка с учётом таймаута."""
        if self.editing_by_user_id is None or self.editing_since is None:
            return False
        cutoff: datetime = datetime.now(timezone.utc) - timedelta(
            minutes=EDITING_LOCK_TIMEOUT_MINUTES
        )
        return self.editing_since > cutoff
```

❌ **НЕПРАВИЛЬНО:**
```python
# ❌ ОШИБКА 1: Нарушение Правила №33 — присваивание в @property
@is_editing_locked.setter
def is_editing_locked(self, value: bool) -> None:
    self._is_locked = value

# ❌ ОШИБКА 2: Учёт только одного поля, без таймаута
@property
def is_editing_locked(self) -> bool:
    return self.editing_by_user_id is not None
    # Если пользователь закрыл браузер без освобождения —
    # блокировка будет «вечной»

# ❌ ОШИБКА 3: Использование локального времени вместо UTC
cutoff = datetime.now() - timedelta(minutes=30)  # ❌ Наивный datetime
```

---

### Часть 2. Требования к схемам (Pydantic)

#### 2.1. `UpdateSchema` — обязательное поле `version`

Схема обновления **обязана** содержать поле `version` с ограничением `ge=1`. Это поле передаётся клиентом при каждом сохранении и используется для оптимистической блокировки.

✅ **ПРАВИЛЬНО:**
```python
class NoteUpdateSchema(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    content: str | None = None
    # ... другие поля ...

    # ✅ Обязательная ожидаемая версия для оптимистической блокировки
    version: int = Field(..., ge=1)
```

❌ **НЕПРАВИЛЬНО:**
```python
class NoteUpdateSchema(BaseModel):
    title: str | None = None
    # ❌ Поле version отсутствует — оптимистическая блокировка невозможна
    # Сервис сохранения не сможет проверить, актуальны ли данные клиента
```

#### 2.2. `ResponseSchema` — обязательные поля блокировки

Схема ответа **обязана** содержать поля для отображения состояния блокировки на фронтенде:

```python
class NoteResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # ✅ Правило №1

    # ... основные поля ...

    # Поля пессимистической блокировки
    editing_by_user_id: uuid.UUID | None = None
    editing_since: datetime | None = None
    is_editing_locked: bool = False  # ✅ Вычисляемое поле из @property

    # Поле оптимистической блокировки
    version: int
```

---

### Часть 3. Требования к CRUD: `acquire_editing_lock`

#### 3.1. Атомарность захвата

Захват блокировки **обязан** выполняться атомарно через `UPDATE ... WHERE ... RETURNING`. Запрещено разделять проверку и установку на два отдельных запроса (это создаёт гонку между двумя пользователями).

#### 3.2. Условия захвата — строго два случая

Блокировка может быть захвачена **только** в двух случаях:
1. Документ свободен: `editing_by_user_id IS NULL`
2. Блокировка истекла: `editing_since < cutoff`

✅ **ПРАВИЛЬНО:**
```python
async def acquire_editing_lock(
    self,
    db: AsyncSession,
    *,
    note_id: uuid.UUID,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    is_superadmin: bool = False,
) -> NotesModel:
    """Атомарный захват блокировки с учётом таймаута."""
    model = self.model

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=EDITING_LOCK_TIMEOUT_MINUTES_LOCAL)

    # ✅ РОВНО ДВА условия для захвата:
    # 1. Документ свободен (никто не редактирует)
    # 2. Блокировка истекла (редактирование длилось > 30 минут)
    conditions: list[ColumnElement[bool]] = [
        model.id == note_id,
        model.deleted_at.is_(None),
        or_(
            model.editing_by_user_id.is_(None),   # ✅ свободно
            model.editing_since < cutoff,          # ✅ истекло
        ),
    ]

    if not is_superadmin:
        conditions.append(model.tenant_id == tenant_id)

    stmt = (
        update(model)
        .where(*conditions)
        .values(editing_by_user_id=user_id, editing_since=now)
        .returning(model.id)
    )

    locked_id = (await db.execute(stmt)).scalar_one_or_none()

    if locked_id is None:
        note = await self.get_for_user(
            db, note_id=note_id, tenant_id=tenant_id,
            is_superadmin=is_superadmin,
        )
        if note is None:
            raise NoteNotFoundError("Заметка не найдена")
        raise NoteEditingLockedError("Документ уже редактируется")

    note = await self.get_for_user(
        db, note_id=note_id, tenant_id=tenant_id,
        is_superadmin=is_superadmin,
    )
    if note is None:
        raise NoteNotFoundError("Заметка не найдена")

    await db.flush()
    await db.refresh(note)
    return note
```

❌ **НЕПРАВИЛЬНО:**
```python
# ❌ ОШИБКА 1: Избыточные условия в or_(), позволяющие перезахват
conditions = [
    model.id == note_id,
    model.deleted_at.is_(None),
    or_(
        model.editing_by_user_id.is_(None),
        model.editing_by_user_id == user_id,     # ❌ Позволяет «перезахватить» свою же блокировку
        model.editing_since.is_(None),           # ❌ АНОМАЛИЯ: если editing_by установлен, а since NULL
        model.editing_since < cutoff,
    ),
]
# Условие `editing_since.is_(None)` разрешает захват, если по какой-то причине
# блокировка установлена, но время не записано. Это состояние не должно возникать,
# но если возникнет — блокировка будет молча перезахвачена другим пользователем.

# ❌ ОШИБКА 2: Разделение проверки и установки на два запроса (гонка)
note = await self.get_for_user(db, note_id=note_id, ...)
if note.editing_by_user_id is not None:
    raise NoteEditingLockedError("Занято")
# ← Между этой проверкой и следующим UPDATE другой пользователь
# может успеть захватить блокировку
note.editing_by_user_id = user_id
note.editing_since = datetime.now(timezone.utc)
await db.flush()

# ❌ ОШИБКА 3: Использование локального времени
now = datetime.now()  # ❌ Наивный datetime без timezone
cutoff = now - timedelta(minutes=30)
```

---

### Часть 4. Требования к CRUD: `release_editing_lock`

#### 4.1. Проверка владельца блокировки

Освобождение блокировки разрешено **только** владельцу блокировки или суперадмину. Попытка освободить чужую блокировку должна возвращать `423`.

✅ **ПРАВИЛЬНО:**
```python
async def release_editing_lock(
    self,
    db: AsyncSession,
    *,
    note_id: uuid.UUID,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    is_superadmin: bool = False,
) -> NotesModel:
    """Освобождение блокировки владельцем или суперадмином."""
    note = await self.get_for_user(
        db, note_id=note_id, tenant_id=tenant_id,
        is_superadmin=is_superadmin,
    )

    if note is None:
        raise NoteNotFoundError("Заметка не найдена")

    # ✅ Проверка: освободить может только владелец или суперадмин
    if (
        not is_superadmin
        and note.editing_by_user_id is not None
        and note.editing_by_user_id != user_id
    ):
        raise NoteEditingLockedError("Блокировка принадлежит другому пользователю")

    note.editing_by_user_id = None
    note.editing_since = None

    await db.flush()
    await db.refresh(note)
    return note
```

❌ **НЕПРАВИЛЬНО:**
```python
# ❌ Любой пользователь может освободить любую блокировку
note.editing_by_user_id = None
note.editing_since = None
await db.flush()
# Пользователь B может освободить блокировку пользователя A
# и начать редактировать документ, пока A работает с модалкой
```

---

### Часть 5. Требования к CRUD: `save_with_version`

#### 5.1. Двойная проверка блокировок

Метод сохранения **обязан** проверять **обе** блокировки:
1. **Пессимистическую** — если документ заблокирован другим пользователем → `423`
2. **Оптимистическую** — если `version` не совпал → `409`

Порядок проверок критичен: сначала пессимистическая (быстрый отказ), затем оптимистическая (атомарный `UPDATE`).

#### 5.2. Жёсткая проверка пессимистической блокировки

Проверка блокировки в `save_with_version` должна быть **жёсткой**: если `editing_by_user_id` установлен и принадлежит другому пользователю, блокировка считается активной **по умолчанию**. Таймаут (`editing_since <= cutoff`) снимает блокировку только как исключение.

✅ **ПРАВИЛЬНО:**
```python
async def save_with_version(
    self,
    db: AsyncSession,
    *,
    note_id: uuid.UUID,
    obj_in: NoteUpdateSchema,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    is_superadmin: bool = False,
) -> NotesModel:
    model = self.model

    note = await self.get_for_user(
        db, note_id=note_id, tenant_id=tenant_id,
        is_superadmin=is_superadmin,
    )

    if note is None:
        raise NoteNotFoundError("Заметка не найдена")

    # ✅ ШАГ 1: ЖЁСТКАЯ проверка пессимистической блокировки
    # Если блокировка установлена и принадлежит другому пользователю,
    # она считается активной, пока не доказано обратное (истечение таймаута)
    if (
        note.editing_by_user_id is not None
        and note.editing_by_user_id != user_id
        and not is_superadmin
    ):
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(minutes=EDITING_LOCK_TIMEOUT_MINUTES_LOCAL)
        # Блокировка активна если:
        # - editing_since не установлен (аномалия, считаем активной)
        # - ИЛИ блокировка не истекла
        if note.editing_since is None or note.editing_since > cutoff:
            raise NoteEditingLockedError(
                "Документ заблокирован другим пользователем для редактирования"
            )

    # ✅ ШАГ 2: Атомарный UPDATE с оптимистической блокировкой
    values: dict[str, Any] = obj_in.model_dump(
        exclude_unset=True, exclude={"version"}
    )
    values["version"] = model.version + 1
    values["updated_at"] = func.now()
    values["updated_by_user_id"] = user_id
    # После сохранения блокировка освобождается
    values["editing_by_user_id"] = None
    values["editing_since"] = None

    conditions: list[ColumnElement[bool]] = [
        model.id == note_id,
        model.version == obj_in.version,  # ✅ Оптимистическая блокировка
        model.deleted_at.is_(None),
    ]

    if not is_superadmin:
        conditions.append(model.tenant_id == tenant_id)

    stmt = (
        update(model)
        .where(*conditions)
        .values(**values)
        .returning(model.id)
    )

    updated_id = (await db.execute(stmt)).scalar_one_or_none()

    if updated_id is None:
        raise NoteVersionConflictError(
            "Документ изменён другим пользователем. Обновите данные."
        )

    await db.flush()
    await db.refresh(note)
    return note
```

❌ **НЕПРАВИЛЬНО:**
```python
# ❌ ОШИБКА 1: Отсутствует проверка пессимистической блокировки
async def save_with_version(self, db, *, note_id, obj_in, ...):
    # Сразу переходим к UPDATE, не проверяя editing_by_user_id
    stmt = update(model).where(
        model.id == note_id,
        model.version == obj_in.version,
    ).values(**values)
    # Пользователь B может сохранить изменения, даже если документ
    # заблокирован пользователем A

# ❌ ОШИБКА 2: Мягкая проверка блокировки (все условия должны быть истинны)
if (
    note.editing_by_user_id is not None
    and note.editing_by_user_id != user_id
    and note.editing_since is not None    # ❌ Если editing_since NULL — проверка пропущена
    and note.editing_since > cutoff
):
    raise NoteEditingLockedError(...)
# Если по какой-то причине editing_since оказался NULL при установленном
# editing_by_user_id, блокировка будет проигнорирована

# ❌ ОШИБКА 3: Блокировка не освобождается после сохранения
values["version"] = model.version + 1
values["updated_by_user_id"] = user_id
# ❌ editing_by_user_id и editing_since остаются заполненными
# → после сохранения документ всё ещё «заблокирован»
# → следующий пользователь не сможет его открыть
```

---

### Часть 6. Требования к CRUD: `mark_deleted`

#### 6.1. Проверка блокировки перед удалением

Удаление заблокированного документа другим пользователем **запрещено**. Проверка идентична проверке в `save_with_version`.

✅ **ПРАВИЛЬНО:**
```python
async def mark_deleted(
    self,
    db: AsyncSession,
    *,
    note_id: uuid.UUID,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    is_superadmin: bool = False,
) -> NotesModel:
    note = await self.get_for_user(
        db, note_id=note_id, tenant_id=tenant_id,
        is_superadmin=is_superadmin,
    )

    if note is None:
        raise NoteNotFoundError("Заметка не найдена")

    # ✅ Проверка пессимистической блокировки перед удалением
    if (
        note.editing_by_user_id is not None
        and note.editing_by_user_id != user_id
        and not is_superadmin
    ):
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(minutes=EDITING_LOCK_TIMEOUT_MINUTES_LOCAL)
        if note.editing_since is None or note.editing_since > cutoff:
            raise NoteEditingLockedError(
                "Документ заблокирован другим пользователем и не может быть удалён"
            )

    note.deleted_at = datetime.now(timezone.utc)
    note.deleted_by_user_id = user_id
    note.updated_by_user_id = user_id
    note.editing_by_user_id = None
    note.editing_since = None
    note.version = note.version + 1

    await db.flush()
    await db.refresh(note)
    return note
```

---

### Часть 7. Требования к роутеру

#### 7.1. Обязательные эндпоинты

Для каждого типа документа с блокировками должны быть реализованы **6 эндпоинтов**:

| Метод | Путь | Назначение | Коды ошибок |
|-------|------|------------|-------------|
| `GET` | `/{doctype}/` | Список документов | — |
| `POST` | `/{doctype}/` | Создание документа | 400 |
| `GET` | `/{doctype}/{id}` | Один документ | 404 |
| `PUT` | `/{doctype}/{id}` | Сохранение с блокировкой | 404, 409, 423, 400 |
| `DELETE` | `/{doctype}/{id}` | Мягкое удаление | 404, 423 |
| `POST` | `/{doctype}/{id}/lock` | Захват блокировки | 404, 423 |
| `DELETE` | `/{doctype}/{id}/lock` | Освобождение блокировки | 404, 423 |

#### 7.2. Обработка исключений

Каждый эндпоинт **обязан** обрабатывать специфичные исключения модуля и преобразовывать их в корректные HTTP-статусы:

✅ **ПРАВИЛЬНО:**
```python
@router.put("/{note_id}", response_model=ApiResponse[NoteResponseSchema])
async def update_note(
    note_id: uuid.UUID,
    obj_in: NoteUpdateSchema,
    current_session: CurrentUser,
    db: DBSession,
) -> ApiResponse[NoteResponseSchema]:
    """Сохранение с проверкой версии (409) и блокировки (423)."""
    try:
        note = await crud_note.save_with_version(
            db,
            note_id=note_id,
            obj_in=obj_in,
            tenant_id=current_session.tenant_id,
            user_id=current_session.id,
            is_superadmin=current_session.is_superadmin,
        )
    except NoteNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except NoteVersionConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except NoteEditingLockedError as exc:
        raise HTTPException(status_code=423, detail=str(exc)) from exc
    except SectionNotInTenantError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    await db.commit()
    await db.refresh(note)

    return ApiResponse(
        success=True,
        message="Заметка сохранена",
        data=NoteResponseSchema.model_validate(note),
    )
```

❌ **НЕПРАВИЛЬНО:**
```python
# ❌ ОШИБКА: Отсутствие обработки NoteEditingLockedError
try:
    note = await crud_note.save_with_version(...)
except NoteNotFoundError as exc:
    raise HTTPException(status_code=404, detail=str(exc)) from exc
except NoteVersionConflictError as exc:
    raise HTTPException(status_code=409, detail=str(exc)) from exc
# ❌ NoteEditingLockedError не обработан → 500 вместо 423
# Фронтенд не сможет отличить «документ занят» от «сервер упал»
```

#### 7.3. Специфичные исключения модуля

Каждый документный модуль обязан определить набор исключений в отдельном файле `exceptions.py`:

```python
class NoteNotFoundError(Exception):
    """Документ не найден или недоступен в текущем тенанте."""

class NoteVersionConflictError(Exception):
    """Ожидаемая версия не совпадает с версией в БД (409)."""

class NoteEditingLockedError(Exception):
    """Документ редактируется другим пользователем (423)."""

class SectionNotInTenantError(Exception):
    """Раздел не существует или не принадлежит организации (400)."""
```

---

### Часть 8. Требования к транзакциям

#### 8.1. Паттерн `flush` в CRUD, `commit` в роутере

В соответствии с правилами проекта (Бэкенд №31, ТЗ §12.1.4):
- **В CRUD** используется только `await db.flush()` — фиксирует изменения в рамках текущей транзакции, но не коммитит.
- **В роутере** после успешного вызова CRUD-метода выполняется `await db.commit()` — единый коммит на весь запрос.

Это гарантирует, что захват блокировки и последующее сохранение/удаление выполняются в одной транзакции, и при любой ошибке всё откатывается.

✅ **ПРАВИЛЬНО:**
```python
# В CRUD:
async def acquire_editing_lock(self, db, ...):
    # ...
    await db.flush()      # ✅ flush в CRUD
    await db.refresh(note)
    return note

# В роутере:
@router.post("/{note_id}/lock", ...)
async def acquire_note_lock(note_id, current_session, db):
    note = await crud_note.acquire_editing_lock(db, ...)
    await db.commit()     # ✅ commit в роутере
    await db.refresh(note)
    return ApiResponse(...)
```

❌ **НЕПРАВИЛЬНО:**
```python
# ❌ commit в CRUD — нарушает единую транзакцию
async def acquire_editing_lock(self, db, ...):
    # ...
    await db.commit()     # ❌ Если роутер после этого упадёт —
    await db.refresh(note) # блокировка уже закоммичена, а ответ не отправлен
    return note
```

---

### Часть 9. Чек-лист применения

Перед коммитом документного модуля проверьте:

**Модель:**
- [ ] Наследует `DocumentAccessMixin` и `DocumentLifecycleMixin`
- [ ] Реализован `@property is_editing_locked` с учётом таймаута
- [ ] `is_editing_locked` использует `datetime.now(timezone.utc)`

**Схемы:**
- [ ] `UpdateSchema` содержит `version: int = Field(..., ge=1)`
- [ ] `ResponseSchema` содержит `editing_by_user_id`, `editing_since`, `is_editing_locked`, `version`
- [ ] `ResponseSchema` имеет `model_config = ConfigDict(from_attributes=True)`

**CRUD — `acquire_editing_lock`:**
- [ ] Захват выполняется атомарно через `UPDATE ... WHERE ... RETURNING`
- [ ] В `or_()` ровно два условия: `editing_by_user_id IS NULL` и `editing_since < cutoff`
- [ ] Нет избыточных условий (`== user_id`, `IS NULL` для `editing_since`)
- [ ] При неудачном захвате выбрасывается `NoteEditingLockedError`
- [ ] Используется `datetime.now(timezone.utc)`

**CRUD — `release_editing_lock`:**
- [ ] Проверка владельца блокировки перед освобождением
- [ ] Суперадмин может освободить чужую блокировку
- [ ] При попытке освободить чужую блокировку — `NoteEditingLockedError`

**CRUD — `save_with_version`:**
- [ ] Проверка пессимистической блокировки **до** атомарного `UPDATE`
- [ ] Проверка жёсткая: `editing_since is None` считается активной блокировкой
- [ ] Атомарный `UPDATE` с условием `version == obj_in.version`
- [ ] При 0 затронутых строк — `NoteVersionConflictError` (409)
- [ ] После сохранения блокировка сбрасывается (`editing_by_user_id = None`)

**CRUD — `mark_deleted`:**
- [ ] Проверка пессимистической блокировки **до** удаления
- [ ] При заблокированном документе — `NoteEditingLockedError` (423)
- [ ] При удалении блокировка сбрасывается

**Роутер:**
- [ ] Реализованы эндпоинты `POST /{id}/lock` и `DELETE /{id}/lock`
- [ ] `PUT /{id}` обрабатывает 404, 409, 423, 400
- [ ] `DELETE /{id}` обрабатывает 404, 423
- [ ] `commit` выполняется в роутере, а не в CRUD

**Исключения:**
- [ ] Файл `exceptions.py` содержит все специфичные исключения модуля
- [ ] Каждое исключение имеет docstring с описанием и HTTP-кодом

---

### Обоснование

#### Почему две блокировки, а не одна?

| Сценарий | Только оптимистическая | Только пессимистическая | Обе |
|----------|----------------------|------------------------|-----|
| Пользователь узнаёт о конфликте | При сохранении (409) | При открытии (423 → readOnly) | При открытии |
| Потеря работы | 10 минут редактирования впустую | Нет | Нет |
| Защита от прямого API-вызова | ✅ Есть (409) | ❌ Нет | ✅ Есть (423 + 409) |
| Защита от «забытых» вкладок | Не нужна | ✅ Таймаут 30 мин | ✅ Таймаут 30 мин |
| Защита от гонок при захвате | Не нужна | ✅ Атомарный `UPDATE` | ✅ Атомарный `UPDATE` |

Оптимистическая блокировка — **последняя линия обороны** на уровне данных. Пессимистическая блокировка — **первая линия обороны** на уровне UX. Обе необходимы, потому что ни одна из них не покрывает все сценарии.

#### Почему жёсткая проверка, а не мягкая?

Мягкая проверка (все условия через `AND`) допускает ситуацию, когда блокировка установлена (`editing_by_user_id` заполнен), но по какой-то причине `editing_since` оказался `NULL`. В этом случае мягкая проверка пропустит сохранение, и пользователь перезапишет чужие изменения.

Жёсткая проверка считает блокировку активной **по умолчанию**, если `editing_by_user_id` установлен и принадлежит другому пользователю. Таймаут снимает блокировку только как исключение. Это соответствует принципу ТЗ §2.2: «При отсутствии любых из необходимых настроек — доступа нет. Ошибка конфигурации приводит к отсутствию доступа, а не к его появлению».

#### Связь с другими правилами

| Правило | Связь |
|---------|-------|
| Бэкенд №1 | `@property` для `is_editing_locked`, `lazy="selectin"` для связей |
| Бэкенд №21 | Именование схем `Create/Update/Response` |
| Бэкенд №26 | Мультиарендность: фильтрация `tenant_id` в каждом запросе |
| Бэкенд №31 | Наследование от `CRUDBase`, `flush` в CRUD, `commit` в роутере |
| Бэкенд №33 | Запрет присваивания в `@property` |
| ТЗ §3.3 | Контракт атрибутов доступа |
| ТЗ §12.2 | Аудит операций с данными (`updated_by_user_id`, `deleted_by_user_id`) |
| Фронтенд №39 | Паттерн «название-ссылка» + режим `readOnly` при 423 |

---

Это правило является обязательным для всех документных модулей проекта. Любое отклонение (отсутствие проверки блокировки в `save_with_version`, мягкая проверка, отсутствие таймаута в `is_editing_locked`) будет считаться критическим нарушением архитектуры и подлежит немедленному исправлению.

---

## Правило №42: Денормализация связанных сущностей для отображения в интерфейсе

**Суть:** Если поле в форме или таблице отображает связанную сущность через `ReferenceSelect` (Правило №27) или в виде текстового значения (например, колонка «Раздел» в списке), бэкенд **обязан** возвращать денормализованное имя связанной сущности в `ResponseSchema`. Это имя заполняется через `@property` в модели, который читает связанный объект, загруженный через `relationship` с `lazy="selectin"`.

Без этого поля фронтенд не сможет отобразить выбранное значение: в списке будет прочерк «—», а в модалке редактирования — пустое поле или placeholder, хотя в БД значение (`section_id`, `tenant_id`, `author_id`) заполнено.

**Область применения:** все модули, использующие `ReferenceSelect` или отображающие связанные сущности в списках. Правило обязательно для документных модулей (`notes` и будущие типы документов) и справочников со связями.

---

### Строгие требования

#### 1. Модель (наследник `Base` и/или миксинов)

1.1. Для каждой связанной сущности, отображаемой в интерфейсе, объявить `relationship` с `lazy="selectin"` (Правило №1).

1.2. Связи **обязательно** типизируются через `Mapped["ModelName"]` с использованием строковых имён и блока `TYPE_CHECKING` для импортов (защита от циклических импортов).

1.3. Если внешний ключ определён в миксине (например, `DocumentAccessMixin.author_id`), в `relationship` используется **строковая форма** `foreign_keys="NotesModel.author_id"`. Прямая ссылка `foreign_keys=[DocumentAccessMixin.author_id]` вызывает `NoForeignKeysError`.

1.4. Реализовать `@property` для получения имени связанной сущности. Имя свойства формируется по схеме `{связь}_name` (например, `section_name`, `tenant_name`, `author_name`).

1.5. `@property` обязан возвращать `str | None` и безопасно обрабатывать отсутствие связи: `return self.section.name if self.section else None`.

#### 2. ResponseSchema (Pydantic)

2.1. Объявить поле `{связь}_name: str | None = None` для каждой денормализованной связи.

2.2. Наличие `model_config = ConfigDict(from_attributes=True)` обязательно (Правило №1) — именно оно позволяет Pydantic читать значения из `@property`.

2.3. Поле `..._name` должно быть объявлено **явно**. Если поле не объявлено в схеме, оно не попадёт в ответ API, даже если `@property` существует в модели.

#### 3. Фронтенд

3.1. В `ReferenceSelect` используется проп `selectedLabel={initialData?.section_name ?? "Выберите..."}` (Правило №27).

3.2. В списках значение выводится напрямую: `{item.section_name ?? "—"}`.

3.3. Если тип из Orval не содержит поля `..._name` (поле добавлено в схему, но Orval ещё не перегенерирован), допускается временное приведение типа `(item as NoteResponseSchema & { section_name?: string })`. После `npm run generate:api` приведение убирается.

---

### ✅ ПРАВИЛЬНО

#### Модель

```python
import uuid
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Index, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.doctypes.document_base import (
    EDITING_LOCK_TIMEOUT_MINUTES,
    DocumentAccessMixin,
    DocumentLifecycleMixin,
)

# ✅ TYPE_CHECKING для избежания циклических импортов
if TYPE_CHECKING:
    from app.core.sections.models import SectionModel
    from app.core.users.models import UserModel


class NotesModel(DocumentAccessMixin, DocumentLifecycleMixin, Base):
    __tablename__ = "notes"
    __table_args__ = (
        Index("ix_notes_tenant_status", "tenant_id", "doc_status"),
        {"schema": "public"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuid_generate_v4()"),
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ✅ Явная типизация связей через Mapped[...] + строковая форма
    # foreign_keys (внешний ключ определён в миксине)
    section: Mapped["SectionModel"] = relationship(
        "SectionModel",
        foreign_keys="NotesModel.section_id",
        lazy="selectin",
    )
    author: Mapped["UserModel"] = relationship(
        "UserModel",
        foreign_keys="NotesModel.author_id",
        lazy="selectin",
    )

    # ✅ Правило №42: @property для денормализации
    @property
    def section_name(self) -> str | None:
        """Название раздела для ReferenceSelect и списков."""
        return self.section.name if self.section else None

    @property
    def author_name(self) -> str | None:
        """Имя автора для отображения."""
        return self.author.name if self.author else None

    # ... другие @property ...
```

#### ResponseSchema

```python
class NoteResponseSchema(BaseModel):
    # ✅ Правило №1: чтение из ORM-атрибутов, включая @property
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    content: str | None = None

    # Контракт доступа (§3.3)
    tenant_id: uuid.UUID
    section_id: uuid.UUID
    author_id: uuid.UUID
    or_tags: list[str] | None = None
    and_tags: list[str] | None = None

    # ✅ Правило №42: денормализованные имена связанных сущностей
    section_name: str | None = None
    author_name: str | None = None

    # ... остальные поля ...
```

#### Фронтенд — список

```tsx
<TableCell style={{ width: widths.section_name }} className="py-1 align-top overflow-hidden">
  <div className="truncate">{item.section_name ?? "—"}</div>
</TableCell>
```

#### Фронтенд — форма (Правило №27)

```tsx
<Controller
  name="section_id"
  control={control}
  render={({ field }) => (
    <ReferenceSelect
      fetchFn={async (params) => {
        const response = await getSectionsSectionsGet(params);
        const items = (response?.data?.items ?? []).map((item) => ({
          id: item.id,
          name: item.name,
        }));
        return { items, total: response?.data?.total ?? 0 };
      }}
      queryKey={["sections", "active"]}
      value={field.value}
      onValueChange={field.onChange}
      placeholder="Выберите раздел..."
      // ✅ Правило №42: денормализованное имя из ResponseSchema
      selectedLabel={initialData?.section_name ?? "Выберите раздел..."}
      heading="Разделы"
      limit={50}
    />
  )}
/>
```

---

### ❌ НЕПРАВИЛЬНО

```python
# ❌ ОШИБКА 1: Нет @property для денормализации
class NotesModel(DocumentAccessMixin, DocumentLifecycleMixin, Base):
    section = relationship("SectionModel", lazy="selectin")
    # Нет section_name → в ResponseSchema нечего сериализовать
```

```python
# ❌ ОШИБКА 2: @property есть, но поле не объявлено в ResponseSchema
class NotesModel(...):
    @property
    def section_name(self) -> str | None:
        return self.section.name if self.section else None

class NoteResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    section_id: uuid.UUID
    # ❌ Нет section_name → поле не попадёт в ответ, фронтенд покажет «—»
```

```python
# ❌ ОШИБКА 3: Отсутствие model_config — @property не читается
class NoteResponseSchema(BaseModel):
    # ❌ Нет ConfigDict(from_attributes=True)
    id: uuid.UUID
    section_name: str | None = None
```

```python
# ❌ ОШИБКА 4: Прямая ссылка на колонку миксина в foreign_keys
section: Mapped["SectionModel"] = relationship(
    "SectionModel",
    foreign_keys=[DocumentAccessMixin.section_id],  # ❌ NoForeignKeysError
    lazy="selectin",
)
# SQLAlchemy не может разрешить колонку миксина в контексте таблицы
# до завершения определения класса
```

```python
# ❌ ОШИБКА 5: Импорт моделей на верхнем уровне → циклический импорт
from app.core.sections.models import SectionModel  # ❌ Возможный цикл
from app.core.users.models import UserModel         # ❌ Возможный цикл
```

```python
# ❌ ОШИБКА 6: Связь без явной типизации
section = relationship("SectionModel", lazy="selectin")  # ❌ Type is unknown
```

```tsx
// ❌ ОШИБКА 7: Отсутствие selectedLabel
<ReferenceSelect
  fetchFn={...}
  value={field.value}
  onValueChange={field.onChange}
  // ❌ Нет selectedLabel → при редактировании поле пустое
/>
```

```tsx
// ❌ ОШИБКА 8: Отладка через prefetchQuery / setQueryData
useEffect(() => {
  queryClient.prefetchQuery({ queryKey: ["sections"], ... });
}, []);
// ❌ Запрещено Правилом №27. Правильное решение — денормализация на бэкенде
```

---

### Диагностика: если связанное поле не отображается

При симптоме «в БД значение есть, а в интерфейсе прочерк или пустое поле» проверьте по порядку:

| Шаг | Что проверить | Где |
|-----|---------------|-----|
| 1 | Объявлена ли связь `relationship` в модели с `lazy="selectin"` | `models.py` |
| 2 | Есть ли `@property {связь}_name` в модели | `models.py` |
| 3 | Объявлено ли поле `{связь}_name` в `ResponseSchema` | `schemas.py` |
| 4 | Есть ли `model_config = ConfigDict(from_attributes=True)` | `schemas.py` |
| 5 | Возвращает ли API поле `{связь}_name` (проверить в `/docs` или сетевых запросах) | Браузер |
| 6 | Перегенерирован ли Orval-клиент (`npm run generate:api`) | `frontend/` |
| 7 | Используется ли `selectedLabel` в `ReferenceSelect` | `EditXxxModal.tsx` |

Если поле отсутствует в ответе API на шаге 5 — проблема на шагах 1–4. Если поле есть в ответе, но отсутствует в типах TypeScript — проблема на шаге 6.

---

### Обоснование

#### Почему денормализация через `@property`, а не отдельный запрос на фронтенде?

| Аспект | Денормализация через `@property` | Отдельный запрос на фронтенде |
|--------|----------------------------------|-------------------------------|
| Производительность | 1 запрос (`lazy="selectin"` подтягивает связи одним `IN (...)`) | N+1 запросов для каждой записи списка |
| Сложность | 3 строки кода (`relationship` + `@property` + поле в схеме) | `useEffect`, `prefetchQuery`, управление кэшем |
| Надёжность | Гарантирована: поле приходит в каждом ответе | Зависит от кэша, состояния загрузки, асинхронных разрывов (Правило №38) |
| Совместимость с Правилом №27 | ✅ Полная | ❌ Правило №27 запрещает `prefetchQuery` для этой задачи |

#### Почему строковая форма `foreign_keys`?

Когда внешний ключ определён в миксине, класс модели ещё не завершил формирование на момент объявления `relationship`. Прямая ссылка `foreign_keys=[DocumentAccessMixin.author_id]` не позволяет SQLAlchemy разрешить колонку в контексте дочерней таблицы и приводит к `NoForeignKeysError`. Строковая форма `"NotesModel.author_id"` разрешается на этапе `configure_mappers()`, который выполняется после регистрации всех моделей.

#### Почему `TYPE_CHECKING`?

Модели могут ссылаться друг на друга (например, `UserModel` ↔ `NotesModel`). Блок `if TYPE_CHECKING:` выполняется только статическими анализаторами (Pyright, mypy), но не в runtime, что исключает циклические импорты и сохраняет строгую типизацию.

---

### Чек-лист применения

Перед коммитом модуля со связями проверьте:

**Модель:**
- [ ] Для каждой отображаемой связи объявлен `relationship` с `lazy="selectin"`
- [ ] Связи типизированы через `Mapped["ModelName"]`
- [ ] Импорты связанных моделей внутри `if TYPE_CHECKING:`
- [ ] Для внешних ключей из миксинов использована строковая форма `foreign_keys="ModelName.column"`
- [ ] Реализован `@property {связь}_name` с безопасной проверкой `if self.{связь} else None`

**Схема:**
- [ ] В `ResponseSchema` объявлено поле `{связь}_name: str | None = None`
- [ ] Присутствует `model_config = ConfigDict(from_attributes=True)`

**Фронтенд:**
- [ ] В списках выводится `item.{связь}_name ?? "—"`
- [ ] В `ReferenceSelect` указан `selectedLabel={initialData?.{связь}_name ?? "Выберите..."}`
- [ ] После изменения схем выполнен `npm run generate:api`

---

### Связь с другими правилами

| Правило | Связь |
|---------|-------|
| Бэкенд №1 | `lazy="selectin"` для связей, `@property` для вычисляемых полей, `ConfigDict(from_attributes=True)` |
| Бэкенд №33 | `@property` только для чтения, без присваиваний |
| Бэкенд №21 | Суффикс `..._name` согласуется с именованием полей в `ResponseSchema` |
| Фронтенд №27 | `selectedLabel` использует денормализованное поле из `ResponseSchema` |
| Фронтенд №38 | Денормализация исключает асинхронные разрывы при отображении связанных данных |
| ТЗ §3.3 | Контракт атрибутов доступа (связи `tenant`, `section`, `author`) |

---

Это правило обязательно для всех модулей со связями. Любое отклонение (отсутствие поля в `ResponseSchema`, использование `prefetchQuery` для отображения имени, прямая ссылка на колонку миксина в `foreign_keys`) будет считаться нарушением архитектуры и подлежит исправлению при код-ревью.

**Рекомендация:** сохраните правило под номером **№42** в `backend_rules` (так как основная часть требований относится к бэкенду), со ссылкой на Правило №27 фронтенда.

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