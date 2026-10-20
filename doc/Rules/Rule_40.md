# Правило №34: Требования к Backend для корректной работы блокировок редактирования документов

**Суть:** Любой тип документа, наследующий `DocumentLifecycleMixin`, обязан реализовывать **двухуровневую систему блокировок** — оптимистическую (поле `version`) и пессимистическую (поля `editing_by_user_id` + `editing_since`). Оба механизма должны быть согласованы между собой на уровне CRUD-методов и роутера. Нарушение любого из требований приводит либо к потере данных (перезапись чужих изменений), либо к невозможности редактирования (вечная блокировка), либо к ложному ощущению безопасности (пользователь редактирует, не зная, что документ занят).

Правило обязательно для всех модулей, реализующих контракт документов (ТЗ §3.3 + жизненный цикл). Эталонная реализация — модуль `notes`.

---

## Часть 1. Требования к модели (наследник `DocumentLifecycleMixin`)

### 1.1. Обязательные поля

Миксин `DocumentLifecycleMixin` уже содержит все необходимые поля. Наследник **не должен** переопределять или дублировать их:

| Поле | Тип | Назначение |
|------|-----|------------|
| `version` | `Integer NOT NULL DEFAULT 1` | Оптимистическая блокировка |
| `editing_by_user_id` | `UUID NULL FK → users.id` | Пессимистическая блокировка: кто редактирует |
| `editing_since` | `DateTime(timezone=True) NULL` | Пессимистическая блокировка: когда начал |

### 1.2. Обязательное вычисляемое поле `is_editing_locked`

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

## Часть 2. Требования к схемам (Pydantic)

### 2.1. `UpdateSchema` — обязательное поле `version`

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

### 2.2. `ResponseSchema` — обязательные поля блокировки

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

## Часть 3. Требования к CRUD: `acquire_editing_lock`

### 3.1. Атомарность захвата

Захват блокировки **обязан** выполняться атомарно через `UPDATE ... WHERE ... RETURNING`. Запрещено разделять проверку и установку на два отдельных запроса (это создаёт гонку между двумя пользователями).

### 3.2. Условия захвата — строго два случая

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

## Часть 4. Требования к CRUD: `release_editing_lock`

### 4.1. Проверка владельца блокировки

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

## Часть 5. Требования к CRUD: `save_with_version`

### 5.1. Двойная проверка блокировок

Метод сохранения **обязан** проверять **обе** блокировки:
1. **Пессимистическую** — если документ заблокирован другим пользователем → `423`
2. **Оптимистическую** — если `version` не совпал → `409`

Порядок проверок критичен: сначала пессимистическая (быстрый отказ), затем оптимистическая (атомарный `UPDATE`).

### 5.2. Жёсткая проверка пессимистической блокировки

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

## Часть 6. Требования к CRUD: `mark_deleted`

### 6.1. Проверка блокировки перед удалением

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

## Часть 7. Требования к роутеру

### 7.1. Обязательные эндпоинты

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

### 7.2. Обработка исключений

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

### 7.3. Специфичные исключения модуля

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

## Часть 8. Требования к транзакциям

### 8.1. Паттерн `flush` в CRUD, `commit` в роутере

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

## Часть 9. Чек-лист применения

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

## Обоснование

### Почему две блокировки, а не одна?

| Сценарий | Только оптимистическая | Только пессимистическая | Обе |
|----------|----------------------|------------------------|-----|
| Пользователь узнаёт о конфликте | При сохранении (409) | При открытии (423 → readOnly) | При открытии |
| Потеря работы | 10 минут редактирования впустую | Нет | Нет |
| Защита от прямого API-вызова | ✅ Есть (409) | ❌ Нет | ✅ Есть (423 + 409) |
| Защита от «забытых» вкладок | Не нужна | ✅ Таймаут 30 мин | ✅ Таймаут 30 мин |
| Защита от гонок при захвате | Не нужна | ✅ Атомарный `UPDATE` | ✅ Атомарный `UPDATE` |

Оптимистическая блокировка — **последняя линия обороны** на уровне данных. Пессимистическая блокировка — **первая линия обороны** на уровне UX. Обе необходимы, потому что ни одна из них не покрывает все сценарии.

### Почему жёсткая проверка, а не мягкая?

Мягкая проверка (все условия через `AND`) допускает ситуацию, когда блокировка установлена (`editing_by_user_id` заполнен), но по какой-то причине `editing_since` оказался `NULL`. В этом случае мягкая проверка пропустит сохранение, и пользователь перезапишет чужие изменения.

Жёсткая проверка считает блокировку активной **по умолчанию**, если `editing_by_user_id` установлен и принадлежит другому пользователю. Таймаут снимает блокировку только как исключение. Это соответствует принципу ТЗ §2.2: «При отсутствии любых из необходимых настроек — доступа нет. Ошибка конфигурации приводит к отсутствию доступа, а не к его появлению».

### Связь с другими правилами

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