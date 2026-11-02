# Контекст проекта Cool ERP для передачи в новый чат

## 0. Формат предоставления результатов в чате

Пользователь работает в чате. Для удобства копирования файлов полный текст новых/изменённых компонентов `*.tsx` и `*.py` предоставляется в специальных окнах для кода (typescript или python). Ответы даются на русском языке.

---

## 1. Общие сведения о проекте

**Cool ERP** — мульти-tenant ERP-система для управления документами, ролями и полномочиями.

### Стек технологий

| Слой | Технологии |
|------|-----------|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0 (async), PostgreSQL, Pydantic v2 |
| Frontend | React 18, Vite, TypeScript (strict), shadcn/ui, Tailwind CSS |
| API-клиент | Orval (генерация из OpenAPI), React Query (TanStack Query) |
| Формы | React Hook Form + Zod (валидация) |
| Авторизация | Cookie-based (не JWT в заголовках) |
| Миграции БД | Ручные SQL-скрипты (не Alembic autogenerate) |

### Авторизация (Cookie-based)

- Axios настроен с `withCredentials: true`
- CORS на бэкенде: `allow_credentials=True`, `allow_origins=["http://localhost:5173"]` (не `"*"`)
- Cookie: `samesite="lax"`, `secure=False` (для localhost)
- В `dependencies.py` используется `getattr(current_user, "is_superadmin", False)`, а не `.get()`, так как `current_user` — это ORM-объект

### База данных

- PostgreSQL с явной схемой `public`
- Все таблицы создаются через ручные SQL-скрипты
- UUID используется как первичный ключ во всех таблицах
- Связи настраиваются через `relationship` с `back_populates` и `lazy="selectin"`

---

## 2. Архитектура модульного монолита

### 2.1. Два уровня структуры

| Уровень | Назначение | Изоляция |
|---------|-----------|----------|
| **Ядро (`core`)** | Платформа: мульти-арендность, пользователи, роли, разделы, полномочия, типы документов, справочники. Инфраструктура репликации между доменами. | Общее для всех доменов. Не импортирует домены. |
| **Домены (модули)** | Изолированные бизнес-области с собственными таблицами, моделями, сервисами и API. | Изолированы друг от друга. Имеют доступ к ядру. |

### 2.2. Принципы архитектуры

| № | Принцип | Формулировка |
|---|---------|--------------|
| 1 | Изоляция данных доменов | Домен А не делает `SELECT` из таблиц домена Б |
| 2 | Доступность ядра | Любой домен может использовать таблицы ядра через F-Keys и JOINs |
| 3 | Запрет F-Keys между доменами | Связи между доменами только через репликацию |
| 4 | Сервисный интерфейс | Междоменное взаимодействие — через публичные сервисы или реплики |
| 5 | Мастер-реплика | Сущность принадлежит одному домену; другие домены хранят реплики |
| 6 | Транзакционная гарантия | События фиксируются в той же транзакции, что и основное изменение (outbox) |
| 7 | Строгий порядок | События одной логической группы применяются строго последовательно |
| 8 | Идемпотентность | Повторная доставка события не приводит к повторному применению |
| 9 | Единое развёртывание | Один процесс, одна БД, логически изолированные модули |
| 10 | Полнота контракта доступа | Реплика хранит ВСЕ поля контракта доступа (§3.3 ТЗ) |

### 2.3. Матрица доступа

| Источник → Цель | Ядро | Домен А | Домен Б |
|-----------------|:----:|:-------:|:-------:|
| **Ядро** | ✅ | ❌ | ❌ |
| **Домен А** | ✅ (F-Keys, JOINs) | ✅ (внутри) | ❌ (только реплика) |
| **Домен Б** | ✅ (F-Keys, JOINs) | ❌ (только реплика) | ✅ (внутри) |

### 2.4. Соглашения по именованию

| Уровень | Префикс | Пример |
|---------|---------|--------|
| Ядро (бизнес-сущности) | Без префикса | `tenants`, `users`, `roles`, `sections`, `permissions`, `doctypes`, `domains`, `periods`, `currencies` |
| Ядро (инфраструктура) | `core_` | `core_outbox`, `core_inbox`, `core_replication_tasks`, `core_sequence_counters`, `core_replication_progress` |
| Домен | `{domain}_` | `sales_regions`, `bp_companies`, `oper_goods` |
| Реплика между доменами | `{domain}_{source_domain}_{entity}_replica` | `bp_sales_regions_replica`, `sales_oper_goods_replica` |

### 2.5. Существующие домены

| Домен | Префикс | Сущности |
|-------|---------|----------|
| `sales` | `sales_` | `sales_goods` (товары), `sales_regions` (регионы) |
| `inventory` | `inv_` | `inv_warehouses` (склады) |
| `business_partners` | `bp_` | `bp_companies` (компании) |
| `operations` | `oper_` | `oper_goods`, `oper_legal_entities`, `oper_locations`, `oper_persons`, `oper_regions`, `oper_vat_invoices`, `oper_warehouses`, `oper_bank_accounts` (запланировано) |

---

## 3. Механизм репликации между доменами

### 3.1. Общая схема

```
МАСТЕР-ДОМЕН
  1. Бизнес-транзакция (создание/изменение сущности)
  2. Атомарное увеличение счётчика группы (core_sequence_counters)
  3. Запись события в outbox (core_outbox)
  4. COMMIT (основное изменение + событие + счётчик)
        │
        ▼
РЕПЛИКАТОР (фоновый процесс, каждые 2 сек)
  5. Чтение необработанных событий из core_outbox
  6. Создание задач для каждого подписанного домена (core_replication_tasks)
  7. Пометка события как обработанного
        │
        ▼
ПРИМЕНЕНИЕ ЗАДАЧ
  8. Выборка задач со строгим порядком (sequence_no = last_applied + 1)
  9. Проверка идемпотентности (core_inbox)
 10. Адвайзорная блокировка по ordering_key
 11. Применение изменения к реплике (включая контракт доступа)
 12. Обновление прогресса группы (core_replication_progress)
 13. Запись в core_inbox
 14. COMMIT
```

### 3.2. Ключ упорядочивания (ordering_key)

Все события с одним ключом применяются строго последовательно, события с разными ключами — параллельно.

| Сценарий | Ключ упорядочивания |
|----------|---------------------|
| Жизненный цикл сущности | `{домен}:{сущность}:{id}` |
| Движения товара на складе | `stock:{warehouse_id}:{goods_id}` |

### 3.3. Таблицы инфраструктуры репликации

| Таблица | Назначение |
|---------|-----------|
| `core_outbox` | Исходящие события (транзакционный outbox) |
| `core_sequence_counters` | Счётчики последовательности по ключам |
| `core_inbox` | Обработанные события (идемпотентность) |
| `core_replication_tasks` | Очередь задач на синхронизацию |
| `core_replication_progress` | Прогресс применения по группам |
| `core_replication_metrics` | Метрики репликации |

### 3.4. Публикация событий

События публикуются через `OutboxPublisher.publish()` в той же транзакции, что и основное изменение. Для событий с упорядочиванием используется `publish_ordered()` с `ordering_key`.

**Обязательное требование (ТЗ репликации §4.10):** если мастер-сущность наследует `DocumentAccessMixin`, `payload` события ОБЯЗАН содержать все 5 полей контракта доступа:

```python
payload={
    "id": str(entity.id),
    # ... бизнес-данные ...
    "tenant_id": str(entity.tenant_id),
    "section_id": str(entity.section_id),
    "author_id": str(entity.author_id),
    "or_tags": list(entity.or_tags or []),
    "and_tags": list(entity.and_tags or []),
    "is_deleted": False,
}
```

### 3.5. Обработчики репликации

Обработчики регистрируются в `app/core/events/handlers.py` через `register_handler()`. Регистрация происходит при импорте модуля `handlers.py` домена-получателя. Импорт обработчиков добавляется в `main.py`.

**Структура реплики:**
- `region_id` / `goods_id` — PK, ID оригинала (БЕЗ ForeignKey на чужой домен)
- Бизнес-данные (скопированные поля)
- Контракт доступа: `tenant_id`, `section_id`, `author_id`, `or_tags`, `and_tags`
- Метаданные синхронизации: `replica_version`, `replica_synced_at`, `is_deleted`

### 3.6. Интервал опроса и подписка

- Интервал опроса: `Replicator.POLL_INTERVAL = 2.0` секунды
- Подписка через `LISTEN/NOTIFY` не реализована (только поллинг)
- Для снижения задержки возможен гибридный подход (подписка + страховочный поллинг)

### 3.7. Реализованные репликации

| Мастер-домен | Сущность | Домен-получатель | Таблица реплики |
|-------------|----------|------------------|-----------------|
| `sales` | `sales_regions` | `business_partners` | `bp_sales_regions_replica` |

---

## 4. Система разграничения доступа (RBAC/ABAC v2.1)

### 4.1. Слои разграничения доступа

```
Слой 1: Тенант       — жёсткая изоляция данных (исключение — раздел «Общий»)
Слой 2: Раздел       — ВИДИМОСТЬ (явно в роли)
Слой 3: Тип документа — наличие записи Permissions в роли
Слой 4: Теги         — ВИДИМОСТЬ (глобально для Типа документа)
Слой 5: Уровень доступа — ЧТО МОЖНО ДЕЛАТЬ (максимум из ролей)
```

### 4.2. Контракт атрибутов доступа (§3.3)

Любое хранилище документов обязано содержать атрибуты:

| Атрибут | Тип | Назначение |
|---------|-----|-----------|
| `tenant_id` | UUID | Слой 1 |
| `section_id` | UUID | Слой 2 |
| `author_id` | UUID | Уровень «автор» |
| `or_tags` | ARRAY(VARCHAR) | Слой 4, ИЛИ |
| `and_tags` | ARRAY(VARCHAR) | Слой 4, И |

### 4.3. Раздел «Общий» (платформенный) — ключевые правила

| Правило | Формулировка |
|---------|--------------|
| §3.1.2.1 | Документ в разделе «Общий» видим пользователям любой Организации при соблюдении слоёв «Раздел», «Тип документа», «Теги» |
| §4.3.2 | Доступ к документам раздела «Общий» предоставляется только через явное включение этого раздела в роль |
| §4.3.3 | Для всех пользователей, кроме Суперадмина, документы раздела «Общий» доступны только для чтения: уровень = 1, `can_delete = false` |
| §4.3.6 | Создание документа в разделе «Общий» и перемещение в него доступны только Суперадмину |

### 4.4. Уровни доступа (иерархия исправлена в v2.1)

```
4 (полный) > 3 (редактор) > 2 (автор) > 1 (читатель) > 0 (нет доступа)
```

| Уровень | Флаг | Права |
|---------|------|-------|
| Полный (4) | `full_access` | Просмотр, создание, изменение любых записей, удаление, управление тегами |
| Редактор (3) | `editor` | Просмотр + изменение + удаление любых документов типа |
| Автор (2) | `author` | Просмотр + изменение + удаление только своих документов |
| Читатель (1) | `reader` | Только просмотр |
| Нет (0) | — | Запись не существует для пользователя |

**Важно:** Редактор (3) выше Автора (2). Если пользователь имеет оба флага и является автором документа, итоговый уровень = 3.

### 4.5. Право на удаление

- `can_delete` — независимый флаг
- Дополнительно устанавливается автоматически при уровне ≥ 2 (§5.2.4)
- Для не-Суперадмина в разделе «Общий» `can_delete` всегда `false` (§4.3.3)

### 4.6. Режим «только чтение»

Если у пользователя есть право на чтение (уровень ≥ 1), но недостаточный уровень для изменения, документ открывается в режиме «только чтение» (§5.4).

### 4.7. Ключевой вывод по `doctype`

`AccessService._get_doctype()` возвращает `document.__tablename__`. Для модулей в доменах это имя с префиксом (например, `"sales_regions"`). Записи в `doctypes` и `permissions` должны использовать **то же значение**, что и `__tablename__`. Это была причина бага: в `doctypes` был записан код `"regions"`, а сервис искал `"sales_regions"`.

---

## 5. Контракт документов (два миксина)

### 5.1. Структура

Все документы наследуют два миксина из `app/core/doctypes/document_base.py`:

| Миксин | Назначение | Поля |
|--------|-----------|------|
| `DocumentAccessMixin` | Контракт доступа (ТЗ §3.3) | `tenant_id`, `section_id`, `author_id`, `or_tags`, `and_tags` |
| `DocumentLifecycleMixin` | Жизненный цикл | `doc_status`, `doc_number`, `doc_date`, `version`, `editing_by_user_id`, `editing_since`, `created_at`, `created_by_user_id`, `updated_at`, `updated_by_user_id`, `deleted_at`, `deleted_by_user_id` |

### 5.2. Ключевые константы

- `EDITING_LOCK_TIMEOUT_MINUTES = 30` — таймаут пессимистической блокировки
- `DocStatus` — допустимые значения `doc_status`: `draft`, `pending`, `approved`, `active`, `archived`

### 5.3. Вычисляемое поле `is_editing_locked`

Каждый наследник миксинов обязан реализовать `@property is_editing_locked`:

```python
@property
def is_editing_locked(self) -> bool:
    if self.editing_by_user_id is None or self.editing_since is None:
        return False
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=EDITING_LOCK_TIMEOUT_MINUTES)
    return self.editing_since > cutoff
```

### 5.4. Денормализация (Правило №42)

Для отображения связанных сущностей в интерфейсе каждая модель документа реализует:

```python
@property
def tenant_name(self) -> str | None: ...
@property
def section_name(self) -> str | None: ...
@property
def author_name(self) -> str | None: ...
```

Эти поля добавляются в `ResponseSchema` и используются на фронтенде через `selectedLabel` в `ReferenceSelect`.

---

## 6. AccessService

### 6.1. Расположение

`app/core/access/service.py`

### 6.2. Ключевые методы

| Метод | Назначение |
|-------|-----------|
| `resolve_access(user, document, now)` | Вычисление доступа к ОДНОМУ документу (все 9 шагов ТЗ §8.2) |
| `build_access_filter(user, document_model, now)` | SQL-фильтр видимости для СПИСКА документов |
| `build_replica_access_filter(user, replica_model, doctype, now)` | SQL-фильтр видимости для СПИСКА записей реплики (принимает `doctype` явно) |

### 6.3. Протоколы

| Протокол | Назначение |
|----------|-----------|
| `DocumentProtocol` | Контракт экземпляра документа (для `resolve_access`) |
| `DocumentClassProtocol` | Контракт класса модели (для `build_access_filter`) |
| `ReplicaClassProtocol` | Контракт класса модели реплики (для `build_replica_access_filter`) |
| `UserProtocol` | Контракт пользователя |

### 6.4. Совместимость протоколов с моделями (Правило №45)

Статический анализатор не сопоставляет дескрипторы `Mapped[...]` моделей с аннотациями значений в `Protocol`. Решение: `typing_cast("DocumentProtocol", model)` в точке вызова `resolve_access`. Запрещено создавать альтернативные версии протокола (`DocumentProtocolV2` и т.п.).

### 6.5. `_get_doctype` возвращает `__tablename__`

```python
def _get_doctype(self, document: DocumentProtocol) -> str:
    return document.__tablename__
```

Для `SalesRegionModel` это `"sales_regions"`. Записи в `doctypes` и `permissions` должны использовать это же значение.

### 6.6. `_load_candidates` — проверка `perm.tenant_id == user.tenant_id`

В `_load_candidates` Permission ищется по `perm.doctype == doctype AND perm.tenant_id == user.tenant_id`. Это Правило №43: `tenant_id` Permission всегда берётся из связанной роли.

---

## 7. Правила Backend (краткое изложение)

| № | Правило | Ключевые требования |
|---|---------|---------------------|
| 1 | Чистая архитектура и ORM | `@property` для вычисляемых полей, `lazy="selectin"`, `ConfigDict(from_attributes=True)` |
| 4 | Orval-совместимость API | `ApiResponse[PaginatedResponse[T]]` для списков |
| 21 | Именование схем | `...CreateSchema`, `...UpdateSchema`, `...ResponseSchema` |
| 26 | Multi-tenancy | Фильтрация по `tenant_id` на уровне SQL |
| 28 | Схема БД | `{"schema": "public"}`, именованные ограничения |
| 30 | M2M синхронизация | Запрет избыточных таблиц, `cascade="all, delete-orphan"` |
| 31 | Приоритет CRUDBase | Наследование от `CRUDBase`, стандартные имена параметров |
| 32 | Аннотированные типы зависимостей | `DBSession`, `CurrentUser`, `SuperAdminUser` — алиасы |
| 33 | Запрет присваивания в `@property` | `@property` только для чтения |
| 40 | Блокировки редактирования | Двойная блокировка (оптимистическая + пессимистическая), атомарный захват, таймаут 30 мин |
| 42 | Денормализация | `@property` для имён связанных сущностей, `selectedLabel` на фронтенде |
| 43 | `tenant_id` Permission из роли | `tenant_id` всегда из `role.tenant_id`, не из сессии |
| 44 | Типизация динамических конструкций | `sql_cast`, `typing_cast`, `InstrumentedAttribute`, запрет `func.*` для пустоты массивов |
| 45 | Совместимость протоколов | `typing_cast("DocumentProtocol", model)` в точке вызова `resolve_access` |

### Ключевые требования Правила №40 (блокировки)

- `UpdateSchema` содержит `version: int = Field(..., ge=1)`
- `ResponseSchema` содержит `editing_by_user_id`, `editing_since`, `is_editing_locked`, `version`
- `acquire_editing_lock`: атомарный `UPDATE ... WHERE ... RETURNING`, ровно два условия в `or_()`
- `save_with_version`: жёсткая проверка пессимистической блокировки до атомарного `UPDATE`
- `mark_deleted`: проверка блокировки перед удалением
- Роутер: `flush` в CRUD, `commit` в роутере
- Обработка исключений: 404, 409, 423

### Ключевые требования Правила №44 (типизация)

- Запрет `func.cardinality`, `func.coalesce` для проверки пустоты массивов
- Проверка пустоты: `or_(column.is_(None), column.op("=")(empty_array))`
- `sql_cast` для SQL-выражений, `typing_cast` для утверждения типов
- Аннотация `ColumnElement[Sequence[str]]` для `ARRAY` (не `list`)
- Параметр-дескриптор колонки: `InstrumentedAttribute[T]`

---

## 8. Правила Frontend (краткое изложение)

| № | Правило | Ключевые требования |
|---|---------|---------------------|
| 9 | Orval-хуки для API | Все запросы через сгенерированные хуки |
| 11 | Компактные таблицы | `py-1 align-top truncate`, `h-10` для заголовка |
| 12 | Поиск через form | `searchInput` и `search` — раздельные состояния |
| 13 | Фиксированная ширина таблицы | `table-fixed w-full`, `style={{ width }}` |
| 16 | Удаление через AlertDialog | Обязательное подтверждение |
| 17 | Подсветка строки | `bg-yellow-100 dark:bg-yellow-900/30`, 3 секунды |
| 18 | Умная навигация | Поиск страницы с записью после сохранения |
| 20 | Сброс формы | `reset(CREATE_DEFAULTS)` при закрытии |
| 22 | Разделение состояний поиска | `searchInput` vs `search` |
| 24 | `invalidateQueries` ДО закрытия модалки | Строгий порядок действий |
| 25 | `refetch` после удаления | Обновление списка |
| 27 | `ReferenceSelect` | `selectedLabel` обязателен, адаптер в `fetchFn` |
| 29 | Изменяемая ширина колонок | `useResizableColumns`, localStorage |
| 34 | Switch в формах | `checked={field.value}`, `Label` с цветом и иконкой |
| 35 | Вынесение модалок | Отдельный компонент `EditXxxModal.tsx` |
| 36 | Безопасная обработка ошибок | `unknown` вместо `any`, приведение типа |
| 37 | Синхронизация формы при открытии | `useEffect` с `[open, initialData, reset]` |
| 38 | Асинхронная инициализация таблиц | Ожидание загрузки, `useRef` для защиты от повторной инициализации |
| 39 | Название-ссылка с блокировкой | Для документных модулей, `readOnly` при 423 |
| 41 | Общие требования к формам | `react-hook-form` + `zodResolver` + `useToast()` |
| 45 | Совместимость с React Compiler | Предотвращение циклических предупреждений |

### Ключевые требования Правила №39 (название-ссылка с блокировкой)

- Название в первой колонке — кликабельная ссылка (`<button type="button">`)
- Иконка замка при `item.is_editing_locked`
- Кнопка «Редактировать» удалена из колонки «Действия»
- При открытии: проверка `is_editing_locked` → захват блокировки → открытие модалки
- При 423: модалка открывается в режиме `readOnly`
- Режим `readOnly`: все поля `disabled`, кнопка «Сохранить» не рендерится
- При закрытии: освобождение блокировки (если была захвачена)

---

## 9. Формат YAML для генерации форм (`cool-erp-form`)

### 9.1. Назначение

Декларативный формат описания форм для генерации кода. Содержит бизнес-интент формы, технические детали подразумеваются правилами проекта.

### 9.2. Структура

```yaml
meta:
  format_version: "1.2"
  module: ...
  component: ...
  entity: ...
  entity_type: ...
  entity_kind: document | reference   # Ключевой переключатель
  save_mutation: ...
  contract_overrides: ...

titles:
  create: ...
  edit: ...
  copy: ...      # Если поддерживается копирование
  view: ...

dialog:
  width: ...
  max_height: ...

modes:
  create: {}
  edit: {}
  copy:
    source_prop: ...
    name_transform: "{name} (копия)"
    strip_ids_in: [...]
    close_after_save: true
  view:
    trigger: "entity.is_editing_locked or http_423"

data_sources:
  ...

tenant_context:
  effective_tenant:
    priority: [...]
  change_allowed_for: none | admin | superadmin
  ...

tabs:
  - id: ...
    label: ...
    dirty_indicators: [...]
    fields:
      - name: ...
        label: ...
        type: text | textarea | number | date | switch | reference_single | reference_multi_chips | readonly_display
        ...
    parts:
      - type: draft_table | readonly_list
        ...

actions:
  - id: save
    label: ...
    disabled_when: ...
    hidden_when: ...
  - id: cancel
    label_rules: ...

change_indicators:
  ...

events:
  on_open: ...
  on_save_before: ...
  on_save_success: ...
  on_save_error: ...
  on_close: ...

payload:
  ...

mutation_params:
  create: ...
  edit: ...
  copy: ...

business_rules:
  ...
```

### 9.3. Ключевое поле `entity_kind`

| Аспект | `document` | `reference` |
|--------|:---:|:---:|
| Миксины модели | `DocumentAccessMixin` + `DocumentLifecycleMixin` | Нет |
| Поле `section_id` в форме | ✅ Обязательное | ❌ Отсутствует |
| Поля `doc_number`, `doc_date` | ✅ В форме | ❌ Отсутствуют |
| Оптимистическая блокировка (`version`) | ✅ | ❌ |
| Пессимистическая блокировка (`/lock`) | ✅ | ❌ |
| Режим `readOnly` при 423 | ✅ | ❌ |
| Обработка ошибок сохранения | 409, 423, 400 | 400, 404 |

### 9.4. Реализованные формы по YAML

| Форма | YAML | Статус |
|-------|------|--------|
| `EditCompanyModal` | `EditCompanyModal.yaml` | ✅ Реализована, работает |
| `EditRoleModal` | Обратный инжиниринг | ✅ Реализована ранее |
| `EditRegionModal` | YAML с фиксированными `tenant_id`/`section_id` | ✅ Реализована |

---

## 10. Текущее состояние модулей

### 10.1. Ядро (`core`)

| Модуль | Статус |
|--------|--------|
| `auth` | ✅ Полностью рабочий |
| `users` | ✅ Полностью рабочий |
| `tenants` | ✅ Полностью рабочий |
| `roles` | ✅ Полностью рабочий |
| `sections` | ✅ Полностью рабочий |
| `permissions` | ✅ Полностью рабочий |
| `domains` | ✅ Полностью рабочий |
| `doctypes` | ✅ Полностью рабочий |
| `access` (AccessService) | ✅ Реализован с `build_replica_access_filter` |
| `events` (репликация) | ✅ Реализован |

### 10.2. Домен `sales`

| Модуль | Статус |
|--------|--------|
| `goods` (товары) | ✅ Бэкенд + фронтенд, работает |
| `regions` (регионы) | ✅ Бэкенд + фронтенд, работает с `AccessService` |

### 10.3. Домен `inventory`

| Модуль | Статус |
|--------|--------|
| `warehouses` (склады) | ✅ Бэкенд + фронтенд, работает |

### 10.4. Домен `business_partners`

| Модуль | Статус |
|--------|--------|
| `companies` (компании) | ✅ Бэкенд + фронтенд, работает |
| `regions_replica` (реплика регионов) | ✅ Бэкенд, подключена к `AccessService` |

---

## 11. Грабли проекта (известные проблемы и решения)

| № | Проблема | Симптом | Решение |
|---|----------|---------|---------|
| 1 | `"self" is not accessed` в CRUD | Предупреждение линтера | Использовать `self.model` |
| 2 | `Type of parameter "self" is unknown` | Ошибка Pyright | Наследовать от `CRUDBase[Model, CreateSchema, UpdateSchema]` |
| 3 | `Method overrides in incompatible manner` | Ошибка типизации | Имена параметров должны совпадать с базовым классом |
| 4 | `ResponseValidationError: tuple` | 500 ошибка | Проверить запятую после `return ApiResponse(...)` |
| 5 | `CORS error` на конкретном запросе | Ошибка в консоли | Искать 500/401 в терминале, не чинить CORS |
| 6 | `AttributeError: .get() on ORM` | `AttributeError` | Использовать `getattr(obj, "attr", default)` |
| 7 | `IntegrityError is not defined` | `NameError` | Импортировать `from sqlalchemy.exc import IntegrityError` |
| 8 | `Type 'undefined' not assignable to 'boolean'` | Ошибка в Switch | Zod: `.optional()` (не `.default()`) |
| 9 | `Resolver type mismatch` | Ошибка в `useForm` | Не использовать `.default()` в Zod |
| 10 | Switch не переключается | Визуально не реагирует | `checked={field.value}`, `onCheckedChange={field.onChange}` |
| 11 | `ReferenceSelect type error` | `Property 'name' is missing` | Адаптер в `fetchFn`, не менять `ReferenceSelect.tsx` |
| 12 | `role_doctypes unknown import` | Ошибка импорта | Использовать `PermissionModel`, не создавать таблицу |
| 13 | Старые значения в форме создания | Видны данные от редактирования | `reset(CREATE_DEFAULTS)` при закрытии |
| 14 | Домен не отображается при редактировании | Пустое поле `ReferenceSelect` | `selectedLabel={initialData?.domain_name}` |
| 15 | `setState` в `useEffect` вызывает каскадные рендеры | Предупреждение | `watch()` или паттерн с `key` |
| 16 | `unexpected any` в catch | Предупреждение | `unknown` с безопасным приведением |
| 17 | `session.user` AttributeError | Ошибка | `CurrentUser` возвращает сам объект пользователя |
| 18 | `PermissionUpdateSchema` несовместим | Ошибка типизации | Использовать `PermissionUpdateSchema` в `update` |
| 19 | TS1261: `Already included file name differs only in casing` | Ошибка сборки | Переименовать файл в два этапа |
| 20 | `Cannot find name 'reset'` | Ошибка | Деструктуризация `useForm` |
| 21 | `Cannot find name 'CREATE_DEFAULTS'` | Ошибка | Объявить константу вне компонента |
| 22 | `Property 'items' does not exist on type '{}'` | Ошибка при работе с кэшем | Явно типизировать `getQueryData()` |
| 23 | Таблица пустая после F5 (async gap) | Пустой список при перезагрузке | Паттерн из Правила №38 |
| 24 | Модель несовместима с `DocumentProtocol` | Pyright: `"Mapped[UUID]" is not assignable to "UUID"` | `typing_cast("DocumentProtocol", model)` в точке вызова (Правило №45). Не создавать альтернативные протоколы |
| 25 | Репликация не работает | События не применяются | Проверить импорт `handlers.py` в `main.py` |
| 26 | Регионы не видны пользователю с ролью | Пустой список | Проверить `doctype` в `doctypes`/`permissions` — должен совпадать с `__tablename__` |
| 27 | Папка не генерируется после `generate:api` | Отсутствует папка в `api/generated/` | Проверить подключение роутера в `main.py` и перезапуск бэкенда |

---

## 12. Ключевые файлы и их назначение

### 12.1. Бэкенд — ядро

| Файл | Назначение |
|------|-----------|
| `app/core/database.py` | `Base`, `get_db`, `engine`, `async_session` |
| `app/core/schemas.py` | `ApiResponse`, `PaginatedResponse` |
| `app/core/crud/base.py` | `CRUDBase` + `@with_db_error_handling` |
| `app/core/auth/dependencies.py` | `DBSession`, `CurrentUser`, `SuperAdminUser` |
| `app/core/doctypes/document_base.py` | `DocumentAccessMixin`, `DocumentLifecycleMixin`, `DocStatus`, `EDITING_LOCK_TIMEOUT_MINUTES` |
| `app/core/access/service.py` | `AccessService` с `resolve_access`, `build_access_filter`, `build_replica_access_filter` |
| `app/core/access/schemas.py` | `AccessResult`, `AccessSource`, `UserProtocol`, константы уровней |
| `app/core/events/models.py` | `CoreOutboxModel`, `CoreInboxModel`, `CoreReplicationTaskModel`, `CoreReplicationProgressModel` |
| `app/core/events/outbox.py` | `OutboxPublisher` |
| `app/core/events/replicator.py` | `Replicator` (фоновый процесс) |
| `app/core/events/handlers.py` | `ReplicaHandler` протокол, `REPLICATION_HANDLERS`, `register_handler` |

### 12.2. Бэкенд — домены

| Домен | Путь | Сущности |
|-------|------|----------|
| `sales` | `app/modules/sales/` | `goods/`, `regions/` |
| `inventory` | `app/modules/inventory/` | `warehouses/` |
| `business_partners` | `app/modules/business_partners/` | `companies/`, `regions_replica/` |

### 12.3. Фронтенд

| Путь | Назначение |
|------|-----------|
| `frontend/src/api/generated/` | Orval-сгенерированные хуки |
| `frontend/src/components/ui/` | shadcn/ui компоненты |
| `frontend/src/lib/reusable/ReferenceSelect.tsx` | Универсальный справочник (НЕ менять) |
| `frontend/src/lib/reusable/ReferenceMultiSelectChips.tsx` | Мультиселект с чипсами (НЕ менять) |
| `frontend/src/core/` | Модули ядра (роли, пользователи, разделы) |
| `frontend/src/modules/` | Модули доменов |

---

## 13. Незавершённые задачи и следующие шаги

### 13.1. Текущие задачи

| Задача | Статус |
|--------|--------|
| Подключение справочника регионов в `EditCompanyModal` через реплику с `AccessService` | 🔄 В процессе — бэкенд готов, фронтенд требует `npm run generate:api` и обновления импорта |
| Домен `operations` | ⏳ Запланирован, не реализован |

### 13.2. Долгосрочные задачи

| Задача | Приоритет |
|--------|-----------|
| Реализация домена `operations` (8 сущностей) | Средний |
| Механизм делегирования (§11 ТЗ) | Низкий (пока не реализован) |
| `user_role_grants` — таблица назначений ролей с сроками | Низкий (пока используется `user.role_ids`) |
| Подписка на события через `LISTEN/NOTIFY` | Низкий (текущий поллинг достаточен) |
| Аудит данных (`data_audit_log`) | Средний |

---

## 14. Команды разработки

| Команда | Описание |
|---------|----------|
| `cd backend && uvicorn app.main:app --reload` | Запуск бэкенда |
| `cd frontend && npm run dev` | Запуск фронтенда (порт 5173) |
| `cd frontend && npm run generate:api` | Генерация Orval-клиента из OpenAPI |
| `cd frontend && npm run build` | Сборка фронтенда |

---

## 15. Принципы работы в чате

1. Пользователь работает в режиме диалога: формулирует задачу → получает полное решение → применяет → сообщает результат
2. При ошибке пользователь присылает полный текст ошибки и ожидает точечное исправление
3. Пользователь ценит: полные тексты файлов, обоснование решений, чек-листы применения
4. Пользователь не любит: дублирование правил проекта в ответах, избыточные пояснения очевидного
5. При генерации форм пользователь использует YAML-спецификации формата `cool-erp-form`
6. Все решения должны соответствовать правилам проекта и ТЗ

---

Этот документ содержит полный контекст проекта для продолжения работы в новом чате. Все правила, архитектура, текущее состояние и незавершённые задачи зафиксированы.