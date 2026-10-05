# 📋 Правило №33: Запрет присваивания значений в `@property` ORM-моделей

Все вычисляемые поля в ORM-моделях **ОБЯЗАТЕЛЬНО** должны реализовываться через декоратор `@property` и использоваться **только для чтения**. Присваивание значений в `@property` (как напрямую, так и через динамическое создание атрибутов) **КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО**.

---

### 1. Обоснование (Почему это важно)

1. **Семантика `@property`:** Декоратор `@property` в Python создаёт **read-only** атрибут. Попытка присвоить ему значение вызывает ошибку `AttributeError` или нарушает контракт класса.
2. **Типобезопасность:** Анализаторы (Pyright/MyPy) видят `@property` как `property` тип, а не как `list` или `str`. Присваивание `item.tenant_ids = [...]` вызывает ошибку `"list[Any]" is not assignable to "property"`.
3. **Чистая архитектура (Правило №1):** Вычисляемые поля должны вычисляться **на лету** из связанных данных, а не храниться в объекте. Это соответствует принципу "модель знает о своих данных".
4. **Целостность данных:** Если разрешить присваивание `@property`, можно случайно рассинхронизировать вычисляемое значение с реальными данными в связанных таблицах.
5. **Предсказуемость:** Разработчик, видя `@property`, ожидает, что значение вычисляется автоматически. Динамическое присваивание ломает это ожидание.

---

### 2. Обязательные требования к реализации

#### 2.1. Объявление `@property` в ORM-модели
Все вычисляемые поля **ОБЯЗАТЕЛЬНО** должны быть объявлены через `@property` в ORM-модели:

```python
class DoctypeModel(Base):
    # ... обычные поля ...
    
    # ✅ ПРАВИЛЬНО: Вычисляемое поле через @property
    @property
    def tenant_ids(self) -> list[uuid.UUID]:
        """Список ID тенантов — вычисляется из relationship."""
        return [t.id for t in self.tenants] if self.tenants else []
    
    @property
    def domain_name(self) -> str | None:
        """Имя домена — вычисляется из связанной модели."""
        return self.domain.name if self.domain else None
```

#### 2.2. Запрет на присваивание в CRUD-методах
В CRUD-классах **КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО** присваивать значения в `@property`:

```python
# ❌ НЕПРАВИЛЬНО: Присваивание в @property
for item in items:
    item.tenant_ids = [t.id for t in item.tenants]  # 💥 Ошибка типизации!

# ✅ ПРАВИЛЬНО: Ничего не присваиваем — @property вычислит значение автоматически
return items, total
```

#### 2.3. Использование в Pydantic-схемах
Pydantic-схемы **ОБЯЗАТЕЛЬНО** должны использовать `from_attributes=True` и либо обычные поля, либо `@computed_field` для чтения `@property` из ORM-моделей:

**Вариант А: Обычные поля (рекомендуется)**
```python
class DoctypeResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    domain_name: str | None = None  # ✅ Читается из @property модели
    tenant_ids: list[uuid.UUID] = []  # ✅ Читается из @property модели
```

**Вариант Б: `@computed_field` (альтернатива)**
```python
class DoctypeResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    
    @computed_field
    @property
    def domain_name(self) -> str | None:
        return None  # Заглушка — реальное значение из ORM
    
    @computed_field
    @property
    def tenant_ids(self) -> list[uuid.UUID]:
        return []  # Заглушка — реальное значение из ORM
```

#### 2.4. Запрет на динамическое создание атрибутов
**КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО** использовать `setattr()` или прямое присваивание для создания новых атрибутов ORM-объектов:

```python
# ❌ НЕПРАВИЛЬНО: Динамическое создание атрибута
setattr(item, "tenant_ids", [t.id for t in item.tenants])

# ❌ НЕПРАВИЛЬНО: Прямое присваивание несуществующего атрибута
item.computed_field = "value"
```

---

### 3. Примеры кода

#### ✅ ПРАВИЛЬНО: Полный цикл работы с вычисляемыми полями

**Шаг 1. ORM-модель (`models.py`):**
```python
class DoctypeModel(Base):
    __tablename__ = "doctypes"
    __table_args__ = {"schema": "public"}
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    doctype: Mapped[str] = mapped_column(String(128), nullable=False)
    doctype_name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # ✅ Связь с тенантами (M2M)
    tenants = relationship("TenantModel", secondary=doctype_tenants, lazy="selectin")
    
    # ✅ Связь с доменом
    domain = relationship("DomainModel", lazy="selectin")
    
    # ✅ Вычисляемые поля через @property
    @property
    def tenant_ids(self) -> list[uuid.UUID]:
        """ID тенантов — вычисляется из relationship."""
        return [t.id for t in self.tenants] if self.tenants else []
    
    @property
    def domain_name(self) -> str | None:
        """Имя домена — вычисляется из связанной модели."""
        return self.domain.name if self.domain else None
```

**Шаг 2. Pydantic-схема (`schemas.py`):**
```python
class DoctypeResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # ✅ Ключевая настройка
    
    id: uuid.UUID
    doctype: str
    doctype_name: str
    
    # ✅ Обычные поля — Pydantic прочитает их из @property модели
    domain_name: str | None = None
    tenant_ids: list[uuid.UUID] = []
```

**Шаг 3. CRUD-метод (`crud.py`):**
```python
async def get_multi_paginated(
    self, db: AsyncSession, tenant_id: uuid.UUID, ...
) -> tuple[list[DoctypeModel], int]:
    stmt = select(self.model)
    # ... логика запроса ...
    
    items = list((await db.execute(stmt)).scalars().all())
    
    # ✅ НИЧЕГО НЕ ПРИСВАИВАЕМ!
    # @property tenant_ids и domain_name автоматически вычислят значения
    # при вызове DoctypeResponseSchema.model_validate(item) в роутере
    
    return items, total
```

**Шаг 4. Роутер (`router.py`):**
```python
@router.get("/", response_model=ApiResponse[PaginatedResponse[DoctypeResponseSchema]])
async def get_doctypes(...):
    items, total = await crud_doctype.get_multi_paginated(...)
    
    return ApiResponse(
        success=True,
        message="Типы документов получены",
        data=cast(
            PaginatedResponse[DoctypeResponseSchema],
            PaginatedResponse(
                # ✅ model_validate автоматически вызовет @property из ORM-модели
                items=[DoctypeResponseSchema.model_validate(item) for item in items],
                total=total,
                skip=skip,
                limit=limit,
            ),
        ),
    )
```

#### ❌ НЕПРАВИЛЬНО: Присваивание в `@property`

```python
# ❌ ГРУБОЕ НАРУШЕНИЕ ПРАВИЛА №33
async def get_multi_paginated(self, db, tenant_id, ...):
    stmt = select(self.model)
    items = list((await db.execute(stmt)).scalars().all())
    
    # 💥 ОШИБКА: Присваивание в @property
    for item in items:
        item.tenant_ids = [t.id for t in item.tenants]  # ❌ Запрещено!
        item.domain_name = item.domain.name  # ❌ Запрещено!
    
    return items, total
```

**Почему это плохо:**
1. `tenant_ids` — это `@property`, а не обычное поле. Присваивание вызывает ошибку типизации.
2. Анализатор видит конфликт: `@property` возвращает `list[uuid.UUID]`, но мы пытаемся присвоить `list[Any]`.
3. Это нарушает семантику `@property` — значение должно вычисляться автоматически, а не храниться.

#### ❌ НЕПРАВИЛЬНО: Динамическое создание атрибутов

```python
# ❌ ОШИБКА: Динамическое создание атрибута
for item in items:
    setattr(item, "computed_field", "value")  # ❌ Запрещено!
```

**Почему это плохо:**
1. SQLAlchemy-модели не предназначены для динамического создания атрибутов.
2. Это ломает типобезопасность — анализатор не видит `computed_field` в классе.
3. При сериализации в JSON через Pydantic это поле не попадёт в ответ (если не объявлено в схеме).

#### ❌ НЕПРАВИЛЬНО: Отсутствие `from_attributes=True`

```python
# ❌ ОШИБКА: Схема без from_attributes
class DoctypeResponseSchema(BaseModel):
    # ❌ Нет model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    domain_name: str | None = None
    tenant_ids: list[uuid.UUID] = []

# В роутере:
DoctypeResponseSchema.model_validate(item)
# 💥 ValidationError: Pydantic ожидает словарь, а получил ORM-объект
```

**Почему это плохо:** Без `from_attributes=True` Pydantic не умеет читать `@property` из ORM-объекта. Он ожидает словарь (`dict`), а получает объект с атрибутами.

---

### 4. Нюансы и лучшие практики

#### 4.1. Когда использовать `@computed_field` vs обычные поля

| Ситуация | Рекомендация |
| :--- | :--- |
| Простое вычисляемое поле | Обычное поле в схеме + `from_attributes=True` |
| Сложная логика вычисления | `@computed_field` в схеме |
| Нужно переиспользовать вычисление | `@property` в модели + обычное поле в схеме |
| Поле не должно попадать в JSON | Только `@property` в модели (не объявлять в схеме) |

#### 4.2. Производительность `@property`

`@property` вычисляется **при каждом обращении**. Если вычисление дорогое (например, сложный SQL-запрос), рассмотрите:
1. **Кэширование:** Использовать `@cached_property` из `functools` (но осторожно — кэш привязан к экземпляру).
2. **Предварительная загрузка:** Убедиться, что связанные данные загружены через `lazy="selectin"` или `joinedload`.
3. **Вычисление в SQL:** Если возможно, вычислять значение на стороне БД через `column_property` или гибридные свойства.

#### 4.3. Связь с `lazy="selectin"`

Чтобы `@property` работало эффективно, связанные данные **ОБЯЗАТЕЛЬНО** должны быть загружены:

```python
class DoctypeModel(Base):
    # ✅ lazy="selectin" гарантирует, что tenants загружены одним запросом
    tenants = relationship("TenantModel", secondary=doctype_tenants, lazy="selectin")
    
    @property
    def tenant_ids(self) -> list[uuid.UUID]:
        # ✅ self.tenants уже загружен — нет дополнительного SQL-запроса
        return [t.id for t in self.tenants]
```

Если использовать `lazy="select"` (по умолчанию), обращение к `self.tenants` вызовет **N+1 запросов** — отдельный SQL для каждого объекта.

#### 4.4. Вычисляемые поля без связанных данных

Если вычисляемое поле не зависит от `relationship`, а только от обычных полей:

```python
class UserModel(Base):
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    
    @property
    def full_name(self) -> str:
        """Вычисляется из обычных полей — нет зависимости от relationship."""
        return f"{self.first_name} {self.last_name}"
```

Это самый простой и эффективный случай — вычисление происходит в памяти, без SQL-запросов.

#### 4.5. Связь с Правилом №1 (Чистая архитектура)

Правило №33 — это конкретизация Правила №1 для вычисляемых полей:
- **Правило №1** требует использовать `@property` для вычисляемых полей.
- **Правило №33** запрещает присваивать значения в `@property` и объясняет, как правильно интегрировать их с Pydantic.

#### 4.6. Связь с Правилом №4 (Orval-совместимость)

Вычисляемые поля, объявленные в Pydantic-схеме, автоматически попадают в OpenAPI-спецификацию. Orval сгенерирует для них TypeScript-типы, и фронтенд сможет их использовать как обычные поля.

---

### 5. Типичные ошибки и их исправление

| Ошибка | Исправление |
| :--- | :--- |
| `item.tenant_ids = [...]` в CRUD | Удалить присваивание — `@property` вычислит автоматически |
| `setattr(item, "field", value)` | Объявить `@property` в модели или обычное поле |
| Отсутствие `from_attributes=True` в схеме | Добавить `model_config = ConfigDict(from_attributes=True)` |
| N+1 запросы при обращении к `@property` | Использовать `lazy="selectin"` в `relationship` |
| `"list[Any]" is not assignable to "property"` | Удалить присваивание — это read-only атрибут |
| `ValidationError` при `model_validate()` | Добавить `from_attributes=True` в схему |

---

### 6. Чек-лист для разработчика

При работе с вычисляемыми полями проверьте:

**ORM-модель:**
- [ ] Вычисляемые поля объявлены через `@property`?
- [ ] `@property` возвращает правильный тип (`list[uuid.UUID]`, `str | None` и т.д.)?
- [ ] Связанные данные загружены через `lazy="selectin"` (если используются в `@property`)?
- [ ] Отсутствуют ли попытки присвоить значение в `@property`?

**Pydantic-схема:**
- [ ] Есть ли `model_config = ConfigDict(from_attributes=True)`?
- [ ] Вычисляемые поля объявлены в схеме (обычные поля или `@computed_field`)?
- [ ] Типы полей в схеме совпадают с типами `@property` в модели?

**CRUD-методы:**
- [ ] Отсутствуют ли присваивания вида `item.field = value` для `@property`?
- [ ] Отсутствует ли `setattr(item, "field", value)`?
- [ ] Метод возвращает "чистые" ORM-объекты без модификации?

**Роутеры:**
- [ ] Используется ли `.model_validate()` для конвертации ORM → Pydantic?
- [ ] Pydantic автоматически читает `@property` из ORM-объекта?

**Анализатор кода:**
- [ ] Отсутствуют ли ошибки `"is not assignable to property"`?
- [ ] Отсутствуют ли ошибки `"Cannot assign to attribute"`?
- [ ] Отсутствуют ли предупреждения о динамическом создании атрибутов?

---

### 7. Размещение в структуре правил

Правило №33 добавляется в **ЧАСТЬ 1. АРХИТЕКТУРА И BACKEND**, после Правила №32.

---

### 8. Связь с другими правилами

- **Правило №1 (Чистая архитектура):** `@property` — это стандартный способ вычисляемых полей в ORM.
- **Правило №4 (Orval-совместимость):** Вычисляемые поля попадают в OpenAPI через Pydantic-схемы.
- **Правило №31 (Приоритет CRUDBase):** CRUD-методы не должны модифицировать ORM-объекты.
- **Правило №32 (Аннотированные типы):** Не влияет напрямую, но оба правила улучшают типобезопасность.

---

Следование этому правилу гарантирует, что:
✅ Вычисляемые поля будут работать предсказуемо и эффективно
✅ Анализаторы кода не будут выдавать ложные ошибки
✅ Код будет соответствовать принципам чистой архитектуры
✅ Pydantic корректно конвертировать ORM-объекты в JSON-ответы
✅ Orval сгенерирует правильные TypeScript-типы для фронтенда

Это правило является важной частью экосистемы чистой архитектуры Cool ERP и работает в связке с Правилами №1, №4, №31 и №32.