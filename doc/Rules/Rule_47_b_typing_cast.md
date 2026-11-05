
## Правило №47: Совместимость моделей документов с протоколами `AccessService` (`typing_cast` в точке вызова)

**Суть:** Модели документов, наследующие `DocumentAccessMixin` и `DocumentLifecycleMixin`, передаются в `AccessService.resolve_access()` через `typing_cast(DocumentProtocol, ...)` непосредственно в точке вызова. Это связано с фундаментальным ограничением статической типизации: анализатор не сопоставляет дескрипторы `Mapped[...]` на уровне класса модели с аннотациями значений в `Protocol`. Обход выполняется только через `typing.cast`; создание альтернативных версий протокола запрещено.

**Область применения:** все модули, передающие экземпляры моделей документов в `AccessService.resolve_access()`. Не распространяется на `AccessService.build_access_filter()`, который принимает класс модели и совместим с `DocumentClassProtocol` без приведения типов.

### Строгие требования

1. **Точка применения каста**
   1.1. `typing_cast(DocumentProtocol, ...)` выполняется непосредственно перед передачей экземпляра модели в `AccessService.resolve_access()`.
   1.2. Каст выполняется в одном месте на каждый вызов. Запрещено выносить «универсальные» функции-обёртки для кастования моделей.
   1.3. Перед кастом модель загружается через стандартные методы (`select`, `db.get`, `get_for_user`) и проверяется на `None`.

2. **Импорт и алиас**
   2.1. Импортируется `cast as typing_cast` из `typing`. Алиас обязателен, чтобы не конфликтовать с `sqlalchemy.cast` (Правило №44, часть 3.3).
   2.2. Импортируется `DocumentProtocol` из `app.core.access.service`.
   2.3. Если в файле одновременно используются `sqlalchemy.cast` и `typing.cast` — оба через алиасы (`sql_cast`, `typing_cast`).

3. **Запрет альтернативных протоколов**
   3.1. Запрещено создавать альтернативные версии протокола (`DocumentProtocolV2`, `DocumentProtocolTyped` и т.п.) для обхода ошибки типизации. Единственным протоколом экземпляра является `DocumentProtocol`.
   3.2. Запрещено добавлять в `DocumentProtocol` аннотации `Mapped[...]` — протокол описывает контракт **экземпляра**, а не класса модели.
   3.3. Запрещено менять существующие аннотации полей протокола ради совместимости с конкретной моделью.

4. **Запрет подавления ошибок другими способами**
   4.1. Запрещено использовать `# type: ignore` для подавления ошибки несовместимости модели с протоколом.
   4.2. Запрещено типизировать параметр `document` как `Any` в вызывающем коде.
   4.3. Запрещено менять сигнатуру `resolve_access` ради обхода проверки типов.

5. **Обязательный комментарий**
   5.1. Каждый `typing_cast` в этой ситуации сопровождается комментарием, объясняющим причину: ограничение типизации протоколов с дескрипторами `Mapped`.
   5.2. Комментарий указывает, что в рантайме совместимость гарантирована миксинами.

6. **`build_access_filter` не требует каста**
   6.1. В `AccessService.build_access_filter()` передаётся **класс** модели (`type[Model]`), а не экземпляр. Совместимость с `DocumentClassProtocol` обеспечивается тем, что протокол использует аннотации `Mapped[...]` на уровне класса.
   6.2. Запрещено выполнять `typing_cast` при передаче класса модели в `build_access_filter`.

### ✅ ПРАВИЛЬНО

**Пример 1: передача экземпляра в `resolve_access`**

```python
from typing import cast as typing_cast  # ✅ Алиас (Правило №44, часть 3.3)

from app.core.access.service import AccessService, DocumentProtocol
from app.core.access.schemas import AccessResult
from app.sales.regions.crud import crud_region
from app.sales.regions.exceptions import RegionNotFoundError


async def get_region_with_access(db, region_id, user):
    region = await crud_region.get_by_id(db, id=region_id)
    if region is None:
        raise RegionNotFoundError("Регион не найден")

    access_service = AccessService(db)

    # ✅ typing_cast необходим: статический анализатор не сопоставляет
    # дескрипторы Mapped[... модели] с аннотациями значений протокола.
    # В рантайме совместимость гарантирована миксинами
    # (Правило №45, часть 5.1 — обязательный комментарий).
    region_doc: DocumentProtocol = typing_cast("DocumentProtocol", region)
    access_result: AccessResult = await access_service.resolve_access(
        user, region_doc
    )

    if not access_result.visible:
        raise RegionNotFoundError("Регион не найден")

    return region, access_result
```

**Пример 2: передача класса в `build_access_filter` (без каста)**

```python
from app.core.access.service import AccessService
from app.sales.regions.models import SalesRegionModel


async def list_regions_with_access(db, user):
    access_service = AccessService(db)

    # ✅ Передаётся КЛАСС модели, каст не требуется (Правило №45, часть 6)
    access_filter = await access_service.build_access_filter(
        user, SalesRegionModel
    )

    if access_filter is None:
        return [], 0

    stmt = select(SalesRegionModel).where(access_filter)
    # ... выполнение запроса
```

**Пример 3: совместное использование `sql_cast` и `typing_cast`**

```python
from typing import cast as typing_cast      # ✅ Алиас для статического каста
from sqlalchemy import cast as sql_cast     # ✅ Алиас для SQL-выражения

from app.core.access.service import DocumentProtocol

# SQL-выражение (для запроса)
empty_array = sql_cast([], ARRAY(String))

# Утверждение типа (только для анализатора)
doc: DocumentProtocol = typing_cast("DocumentProtocol", region)
```

### ❌ НЕПРАВИЛЬНО

```python
# ❌ ОШИБКА 1: Создание альтернативного протокола
@runtime_checkable
class DocumentProtocolV2(Protocol):
    """Дубликат протокола с @property для обхода ошибки типизации."""
    @property
    def tenant_id(self) -> uuid.UUID: ...
    # ...

# Почему плохо: дублирование контракта, риск рассинхронизации с
# DocumentProtocol при изменении миксинов. Ошибку типизации это
# всё равно не решает для дескрипторов Mapped.


# ❌ ОШИБКА 2: Добавление Mapped[...] в протокол экземпляра
class DocumentProtocol(Protocol):
    tenant_id: Mapped[uuid.UUID]  # ❌ Протокол описывает экземпляр,
                                   # а не класс модели

# Почему плохо: протокол — контракт значений на экземпляре.
# На экземпляре модели атрибут возвращает uuid.UUID, а не
# Mapped[uuid.UUID]. Такая аннотация сломает совместимость
# с реальными значениями.


# ❌ ОШИБКА 3: Подавление через # type: ignore
access_result = await access_service.resolve_access(
    user, region  # type: ignore[arg-type]
)

# Почему плохо: скрывает реальную причину, затрудняет рефакторинг,
# нарушает принцип явности (ТЗ §2.1).


# ❌ ОШИБКА 4: Использование Any
async def check_access(
    user: UserProtocol,
    document: Any,  # ❌ Нарушение запрета на Any
) -> AccessResult:
    ...


# ❌ ОШИБКА 5: Изменение сигнатуры сервиса ради обхода
class AccessService:
    async def resolve_access(
        self,
        user: UserProtocol,
        document: DocumentProtocol | SalesRegionModel,  # ❌ Union с конкретной моделью
        ...
    ) -> AccessResult:
        ...

# Почему плохо: сигнатура сервиса не должна зависеть от конкретных
# моделей доменов. Каждый новый домен потребует изменения сигнатуры.


# ❌ ОШИБКА 6: Универсальная функция-обёртка для каста
def as_document(model: Any) -> DocumentProtocol:
    return typing_cast("DocumentProtocol", model)  # ❌ Обёртка скрывает причину

# Почему плохо: каст должен быть явным в точке вызова,
# чтобы читающий код понимал, почему выполняется приведение типа.


# ❌ ОШИБКА 7: Каст при передаче класса в build_access_filter
access_filter = await access_service.build_access_filter(
    user,
    typing_cast("type[DocumentClassProtocol]", SalesRegionModel),  # ❌ Не нужен
)

# Почему плохо: класс модели уже совместим с DocumentClassProtocol
# (протокол использует Mapped[...] на уровне класса).


# ❌ ОШИБКА 8: Импорт cast без алиаса при использовании обоих
from typing import cast          # ❌ Конфликт имён
from sqlalchemy import cast      # ❌ Второй импорт перекрывает первый
```

### Обоснование

**Причина несовместимости типов**

| Уровень | Тип атрибута `tenant_id` | Что видит анализатор | Совместимость с протоколом |
|---------|--------------------------|----------------------|:---:|
| Класс модели | `Mapped[uuid.UUID]` | Дескриптор колонки | ❌ |
| Экземпляр модели | `uuid.UUID` | Значение через `__get__` | ⚠️ Анализатор проверяет класс |
| `DocumentProtocol` | `uuid.UUID` | Ожидает значение | ❌ Проверка по классу |

Анализатор проверяет структурную совместимость по аннотациям **класса**, а не по результату дескриптора при доступе через экземпляр. Поэтому `Mapped[uuid.UUID]` не сопоставляется с `uuid.UUID`, даже если в рантайме экземпляр возвращает корректное значение.

**Почему `typing_cast`, а не другие подходы**

| Подход | Решение проблемы | Соответствие правилам |
|--------|:---:|-----------------------|
| `typing_cast` в точке вызова | ✅ | Правило №44 (алиасы), ТЗ §2.1 (явность) |
| `# type: ignore` | ⚠️ Подавляет симптом | ❌ Скрывает причину |
| Альтернативный протокол | ❌ Не решает | ❌ Дублирование контракта |
| `Mapped` в протоколе | ❌ Ломает семантику | ❌ Протокол для экземпляра |
| `Any` | ⚠️ Отключает проверку | ❌ Нарушение запрета на `Any` |
| Union в сигнатуре сервиса | ⚠️ Локально решает | ❌ Зависимость сервиса от доменов |

**Почему каст безопасен**

Модели документов наследуют оба миксина (`DocumentAccessMixin`, `DocumentLifecycleMixin`), которые гарантируют наличие всех полей протокола. Проверка соответствия контракту выполняется статически через наследование и в рантайме через `validate_document_contract()`. `typing_cast` лишь сообщает анализатору то, что уже гарантировано архитектурой.

### Чек-лист применения

Перед коммитом кода, передающего модель в `AccessService`, проверьте:

**Импорты:**
- [ ] `cast` из `typing` импортирован как `typing_cast`
- [ ] `DocumentProtocol` импортирован из `app.core.access.service`
- [ ] Если используется `sqlalchemy.cast` — импортирован как `sql_cast`

**Передача экземпляра в `resolve_access`:**
- [ ] Модель загружена и проверена на `None` до каста
- [ ] Выполнен `typing_cast("DocumentProtocol", model)` в точке вызова
- [ ] Добавлен комментарий с объяснением причины
- [ ] Результат `resolve_access` типизирован как `AccessResult`

**Передача класса в `build_access_filter`:**
- [ ] Передаётся класс модели без каста
- [ ] Не выполняется `typing_cast` для класса

**Запреты:**
- [ ] Не созданы альтернативные протоколы (`DocumentProtocolV2` и т.п.)
- [ ] Не используются `# type: ignore`, `Any` для обхода
- [ ] Не изменена сигнатура `AccessService` ради обхода
- [ ] Не созданы универсальные функции-обёртки для каста

### Связь с другими правилами

| Правило | Связь |
|---------|-------|
| Бэкенд №44 | Алиасы `typing_cast` / `sql_cast` при совместном использовании |
| Бэкенд №33 | `@property` моделей остаются только для чтения |
| Бэкенд №42 | Денормализованные поля модели не влияют на протокол доступа |
| Бэкенд №36 | Запрет `Any` в обработке ошибок распространяется на типизацию протоколов |
| ТЗ §2.1 | Явное управление: каст выполняется явно в точке вызова, не скрыт в обёртках |
| ТЗ §3.3 | Контракт доступа, описываемый протоколом |
| ТЗ §8.2 | Алгоритм `resolve_access`, принимающий документ через протокол |

---

Правило готово к применению. Любое отклонение (альтернативные протоколы, `# type: ignore`, изменение сигнатуры `AccessService`) будет считаться нарушением архитектуры и подлежит исправлению при код-ревью.

---
