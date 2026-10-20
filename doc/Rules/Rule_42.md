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