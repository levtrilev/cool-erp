## Правило №44: Строгая типизация динамических конструкций SQLAlchemy (`func`, `cast`, `ARRAY`) в Pyright strict-режиме

**Суть:** Динамические конструкции SQLAlchemy — `func.*` (генератор функций), `cast`, `literal` с типом `ARRAY`, а также дескрипторы колонок `InstrumentedAttribute` — не типизируются автоматически в strict-режиме Pyright. Это приводит к ошибкам `Type of "cardinality" is unknown`, `Cast[Sequence[str]] is not assignable to ColumnElement[list[str]]`, `InstrumentedAttribute is not assignable to ColumnElement`. Правило устанавливает единые приёмы обхода этих ограничений **без** использования `# type: ignore`, `Any` и `sqlalchemy.cast` там, где нужен `typing.cast`.

**Область применения:** все модули, работающие с массивами (`ARRAY`), агрегатными/скалярными SQL-функциями (`func.cardinality`, `func.coalesce`, `func.array_length`) и построением типизированных SQL-выражений в `AccessService`, CRUD и миграциях.

---

### Строгие требования

#### 1. Запрет прямого использования `func.*` для проверки пустоты массивов

1.1. `func` в SQLAlchemy — это экземпляр `_FunctionGenerator`, атрибуты которого создаются динамически через `__getattr__`. Pyright **не может** вывести тип для `func.cardinality`, `func.coalesce`, `func.array_length` и любого другого атрибута.

1.2. **ЗАПРЕЩЕНО** строить проверку «массив пуст или `NULL`» через `func.coalesce(func.cardinality(column), 0) == 0`.

1.3. **ОБЯЗАТЕЛЬНО** использовать сравнение с пустым массивом через `sql_cast` и оператор `or_`:
- `column.is_(None)` — массив равен `NULL`
- `column.op("=")(empty_array)` — массив равен `[]`

1.4. Проверка `column.is_(None)` должна идти **первым** условием в `or_`. Если массив `NULL`, выражение `NULL = ARRAY[]` вернуло бы `NULL` (а не `FALSE`), и только `or_` с первым условием гарантирует корректный результат.

#### 2. Инвариантность `ColumnElement[_T]` и тип `ARRAY`

2.1. Типовой параметр `ColumnElement[_T]` **инвариантен**: `ColumnElement[Sequence[str]]` ≠ `ColumnElement[list[str]]`. Присваивание возможно только при точном совпадении типа.

2.2. В тайп-стабах SQLAlchemy тип `ARRAY` имеет параметр `Sequence`, а не `list`. Поэтому:
- `sql_cast(value, ARRAY(String))` возвращает `Cast[Sequence[str]]`
- `literal(value, type_=ARRAY(String))` возвращает `BindParameter[Sequence[str]]`

2.3. **ОБЯЗАТЕЛЬНО** аннотировать результат как `ColumnElement[Sequence[str]]`, импортировав `Sequence` из `collections.abc`.

2.4. **ЗАПРЕЩЕНО** аннотировать результат `sql_cast` / `literal` как `ColumnElement[list[str]]` — это вызывает ошибку инвариантности.

#### 3. Разделение `sqlalchemy.cast` и `typing.cast`

3.1. `sqlalchemy.cast` создаёт **реальное SQL-выражение** `CAST(... AS ...)`. Используется для приведения значений в запросах.

3.2. `typing.cast` — только для **статического анализатора**, не создаёт SQL. Используется для утверждения типа результата.

3.3. **ОБЯЗАТЕЛЬНО** использовать алиасы при совместном использовании, чтобы избежать конфликта имён:
- `from sqlalchemy import cast as sql_cast`
- `from typing import cast as typing_cast`

3.4. **ЗАПРЕЩЕНО** импортировать `cast` без алиаса, если в файле нужны обе функции.

#### 4. Совместимость `InstrumentedAttribute` и `ColumnElement`

4.1. `document_model.column_name` на уровне класса модели — это `InstrumentedAttribute[T]` (дескриптор колонки), а **не** `ColumnElement[T]`. В системе типов SQLAlchemy 2.0 `InstrumentedAttribute` не является подтипом `ColumnElement`.

4.2. Если вспомогательный метод принимает дескриптор колонки модели, **ОБЯЗАТЕЛЬНО** типизировать параметр как `InstrumentedAttribute[T]`, импортировав его из `sqlalchemy.orm.attributes`.

4.3. **ЗАПРЕЩЕНО** типизировать параметр как `ColumnElement[T]`, если в него передаётся `document_model.column_name` — это вызывает ошибку `InstrumentedAttribute is not assignable to ColumnElement`.

4.4. Метод `.op("...")(...)` доступен на `InstrumentedAttribute` и возвращает `ColumnElement[bool]` без дополнительных приведений типов.

#### 5. `typing.cast` не решает проблему доступа к `func.*`

5.1. `typing.cast` применяется к **результату** вызова, но ошибка `Type of "cardinality" is unknown` возникает **до** вызова — на этапе разрешения имени `func.cardinality`.

5.2. **ЗАПРЕЩЕНО** пытаться решить проблему `func.*` через `typing_cast("ColumnElement[int]", func.cardinality(column))` — ошибка сохраняется.

5.3. Единственное решение — **полностью исключить** обращение к `func.*` и заменить его типизированными эквивалентами (см. требование 1).

---

### ✅ ПРАВИЛЬНО

#### Проверка пустоты массива (без `func`)

```python
from collections.abc import Sequence

from sqlalchemy import ColumnElement, String, cast as sql_cast, or_
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm.attributes import InstrumentedAttribute


class AccessService:
    # ...

    @staticmethod
    def _is_empty_tags(
        # ✅ Параметр типизирован как InstrumentedAttribute, а не ColumnElement
        column: InstrumentedAttribute[list[str] | None],
    ) -> ColumnElement[bool]:
        """
        NULL и пустой массив трактуются одинаково: тегов нет.

        ✅ Реализация без `func` (cardinality/coalesce): эти динамические
        атрибуты _FunctionGenerator не типизируются в strict-режиме.
        Вместо них — сравнение с пустым массивом через SQL-операторы.
        """
        empty_tags: list[str] = []
        # ✅ sql_cast (из sqlalchemy) создаёт CAST(:param AS varchar[])
        # ✅ Аннотация ColumnElement[Sequence[str]] — ARRAY использует Sequence
        empty_array: ColumnElement[Sequence[str]] = sql_cast(
            empty_tags,
            ARRAY(String),
        )

        return or_(
            column.is_(None),             # ✅ первым: массив равен NULL
            column.op("=")(empty_array),  # массив равен []
        )
```

#### Типизированный ARRAY-bind для операторов `&&` и `<@`

```python
from collections.abc import Sequence

from sqlalchemy import ColumnElement, String, literal, or_
from sqlalchemy.dialects.postgresql import ARRAY


# Внутри метода, где нужны теги пользователя как SQL-операнд:
user_tags: list[str] = list(user.tags or [])
tags_pass_parts: list[ColumnElement[bool]] = []

if user_tags:
    # ✅ literal возвращает BindParameter[Sequence[str]]
    # ✅ Аннотация ColumnElement[Sequence[str]] точно совпадает с возвратом
    user_tags_sql: ColumnElement[Sequence[str]] = literal(
        user_tags, type_=ARRAY(String)
    )

    if or_enforced:
        # document.or_tags ∩ user.tags ≠ ∅
        # ✅ .op() принимает ColumnElement[Sequence[str]] без приведений
        tags_pass_parts.append(
            or_(or_empty, document_model.or_tags.op("&&")(user_tags_sql))
        )
    if and_enforced:
        # document.and_tags ⊆ user.tags
        tags_pass_parts.append(
            or_(and_empty, document_model.and_tags.op("<@")(user_tags_sql))
        )
```

#### Разделение `sql_cast` и `typing_cast`

```python
# ✅ Алиасы исключают конфликт имён
from typing import cast as typing_cast
from sqlalchemy import cast as sql_cast

# SQL-выражение (для запроса)
empty_array: ColumnElement[Sequence[str]] = sql_cast([], ARRAY(String))

# Утверждение типа (только для анализатора, если действительно нужно)
some_value = typing_cast("ColumnElement[bool]", complex_expression)
```

---

### ❌ НЕПРАВИЛЬНО

#### Ошибка 1: Использование `func.cardinality` / `func.coalesce`

```python
# ❌ Pyright: Type of "cardinality" is unknown, Type of "coalesce" is unknown
@staticmethod
def _is_empty_tags(column: InstrumentedAttribute[list[str] | None]) -> ColumnElement[bool]:
    cardinality_result = typing_cast(
        "ColumnElement[int | None]", func.cardinality(column)  # ❌ ошибка на этапе доступа к func
    )
    coalesced = typing_cast("ColumnElement[int]", func.coalesce(cardinality_result, 0))
    return coalesced == 0
```

**Почему плохо:** `typing.cast` применяется к результату, но ошибка возникает раньше — при разрешении имени `func.cardinality`. Проблема не решается.

#### Ошибка 2: Аннотация `ColumnElement[list[str]]` для результата `sql_cast`/`literal`

```python
# ❌ Type "Cast[Sequence[str]]" is not assignable to "ColumnElement[list[str]]"
empty_array: ColumnElement[list[str]] = sql_cast([], ARRAY(String))

# ❌ Type "BindParameter[Sequence[str]]" is not assignable to "ColumnElement[list[str]]"
user_tags_sql: ColumnElement[list[str]] = literal(user_tags, type_=ARRAY(String))
```

**Почему плохо:** `ColumnElement[_T]` инвариантен. `ARRAY` в тайп-стабах использует `Sequence`, а не `list`. Типы должны совпадать точно.

#### Ошибка 3: Параметр `ColumnElement` вместо `InstrumentedAttribute`

```python
# ❌ InstrumentedAttribute[list[str] | None] is not assignable to ColumnElement[list[str] | None]
@staticmethod
def _is_empty_tags(column: ColumnElement[list[str] | None]) -> ColumnElement[bool]:
    ...

# Вызов:
or_empty = self._is_empty_tags(document_model.or_tags)  # ❌ ошибка типизации
```

**Почему плохо:** `document_model.or_tags` на уровне класса — это `InstrumentedAttribute`, а не `ColumnElement`.

#### Ошибка 4: Конфликт `cast` без алиаса

```python
from typing import cast          # ❌ без алиаса
from sqlalchemy import cast      # ❌ второй импорт перекрывает первый

# Теперь неясно, какой cast используется:
result = cast(x, ARRAY(String))  # ❌ неоднозначность
```

**Почему плохо:** второй импорт молча перекрывает первый. `sqlalchemy.cast` создаёт SQL, `typing.cast` — нет. Поведение зависит от порядка импортов.

#### Ошибка 5: `Any` для подавления ошибок типизации

```python
# ❌ Нарушение запрета на Any
def _is_empty_tags(column: Any) -> Any:
    return func.coalesce(func.cardinality(column), 0) == 0
```

**Почему плохо:** `Any` запрещён Правилом №36 и ТЗ §2.1. Скрывает реальные ошибки типизации.

---

### Обоснование

| Проблема | Причина | Решение правила |
|----------|---------|-----------------|
| `Type of "cardinality" is unknown` | `func` — `_FunctionGenerator` с динамическим `__getattr__` | Заменить `func.*` на сравнение с пустым массивом через `sql_cast` + `or_` |
| `Cast[Sequence[str]]` ≠ `ColumnElement[list[str]]` | `ColumnElement[_T]` инвариантен; `ARRAY` использует `Sequence` | Аннотировать как `ColumnElement[Sequence[str]]` |
| `BindParameter[Sequence[str]]` ≠ `ColumnElement[list[str]]` | Та же инвариантность | Аннотировать как `ColumnElement[Sequence[str]]` |
| `InstrumentedAttribute` ≠ `ColumnElement` | Разные типы в системе типов SQLAlchemy 2.0 | Типизировать параметр как `InstrumentedAttribute[T]` |
| `typing.cast` не помогает с `func.*` | Ошибка возникает до вызова, на этапе разрешения имени | Исключить `func.*` полностью, не пытаться «закастить» |
| Конфликт `cast` | Одно имя в `typing` и `sqlalchemy` | Алиасы `typing_cast` / `sql_cast` |

#### Почему сравнение с пустым массивом вместо `cardinality`

| Аспект | `func.cardinality` | Сравнение через `sql_cast` |
|--------|--------------------|---------------------------|
| Типизация в strict-режиме | ❌ Неизвестный тип | ✅ Полностью типизировано |
| Семантика `NULL` | `cardinality(NULL)` = `NULL`, нужен `coalesce` | `column.is_(None)` обрабатывает `NULL` явно |
| Читаемость | Требует понимания `coalesce` + `cardinality` | Прямое сравнение с `[]` |
| Производительность | Функция БД | Сравнение массивов (оба используют индексы при наличии) |

#### Почему `InstrumentedAttribute`, а не `ColumnElement`

На уровне **класса** модели (`document_model.or_tags`) SQLAlchemy возвращает дескриптор `InstrumentedAttribute`, который при использовании в SQL-выражениях ведёт себя как `ColumnElement`, но формально им не является. На уровне **экземпляра** (`note_instance.or_tags`) это уже значение `list[str] | None`. Правило фиксирует типизацию для уровня класса, где строятся SQL-выражения.

---

### Чек-лист применения

Перед коммитом кода, работающего с `ARRAY` / `func` / `cast`, проверьте:

- [ ] Нет обращений к `func.cardinality`, `func.coalesce`, `func.array_length` для проверки пустоты массивов
- [ ] Проверка пустоты реализована через `or_(column.is_(None), column.op("=")(empty_array))`
- [ ] `column.is_(None)` стоит **первым** условием в `or_`
- [ ] Результат `sql_cast(..., ARRAY(...))` аннотирован как `ColumnElement[Sequence[str]]`
- [ ] Результат `literal(..., type_=ARRAY(...))` аннотирован как `ColumnElement[Sequence[str]]`
- [ ] `Sequence` импортирован из `collections.abc`
- [ ] Параметры-дескрипторы колонок типизированы как `InstrumentedAttribute[T]`
- [ ] `InstrumentedAttribute` импортирован из `sqlalchemy.orm.attributes`
- [ ] `sqlalchemy.cast` импортирован как `sql_cast`
- [ ] `typing.cast` импортирован как `typing_cast` (если используется)
- [ ] Нет `# type: ignore`, `Any` или «голого» `cast` без алиаса

---

### Связь с другими правилами

| Правило | Связь |
|---------|-------|
| Бэкенд №36 (безопасная обработка ошибок) | Запрет `Any` — правило №44 предлагает типизированные альтернативы вместо `Any` |
| Бэкенд №1 (чистая архитектура и ORM) | `InstrumentedAttribute` — часть системы типов SQLAlchemy 2.0, используемая в моделях |
| Бэкенд №42 (денормализация) | Теги документа (`or_tags`, `and_tags`) — массивы, к которым применяется правило №44 |
| ТЗ §3.3 | Контракт атрибутов доступа включает `or_tags`, `and_tags` (ARRAY) |
| ТЗ §6 | Проверка тегов требует корректной типизации массивов в `AccessService` |

---

Это правило обязательно для всех модулей, строящих типизированные SQL-выражения с массивами и динамическими функциями. Любое отклонение (использование `func.cardinality`, аннотация `ColumnElement[list[str]]` для `ARRAY`, «голой» `cast`) будет считаться нарушением и подлежит исправлению при код-ревью.