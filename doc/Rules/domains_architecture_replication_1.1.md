# Техническое задание: Архитектура модульного монолита с механизмом репликации между доменами

**Версия:** 1.1
**Дата:** 01 ноября 2026
**Проект:** Cool ERP

## Изменения относительно версии 1.0

| № | Было (v1.0) | Стало (v1.1) | Раздел |
|---|-------------|--------------|--------|
| 1.1 | Реплика хранила только бизнес-данные + `tenant_id` | Реплика обязана хранить **полный контракт доступа** (5 полей `DocumentAccessMixin`): `tenant_id`, `section_id`, `author_id`, `or_tags`, `and_tags` | §1.2, §4.10, §5.1 |
| 1.2 | Домен-получатель не мог вычислять уровень доступа к реплике | Домен-получатель вычисляет доступ через `AccessService` по полям реплики (ТЗ RBAC/ABAC §8) | §4.10.5 |
| 1.3 | `payload` события содержал только бизнес-поля | `payload` обязан содержать все поля контракта доступа | §4.10.4, §7.1 |
| 1.4 | В реплике отсутствовали индексы для тегов | Добавлены GIN-индексы на `or_tags`, `and_tags` и индекс на `section_id` | §5.1 |

**Обоснование изменения:** без полей контракта доступа в реплике домен-получатель не может выполнить шаги 3–7 алгоритма `resolve_access` (ТЗ RBAC/ABAC §8.2): видимость по разделам, уровень «автор», тег-проверку. Это нарушало принцип «безопасность по умолчанию» (ТЗ §2.2) — доступ к репликам не контролировался.

---

## 1. Концепция архитектуры

### 1.1. Два уровня структуры

Cool ERP построен на архитектуре **Ядро + Домены**, где ядро обеспечивает общую инфраструктуру, а домены — изолированные бизнес-области.

| Уровень | Назначение | Изоляция |
|---------|-----------|----------|
| **Ядро (`core`)** | Платформа: мульти-арендность, пользователи, роли, разделы, полномочия, типы документов, справочники (периоды, валюты). Инфраструктура репликации между доменами. | Общее для всех доменов. Не импортирует домены. |
| **Домены (модули)** | Изолированные бизнес-области с собственными таблицами, моделями, сервисами и API. | Изолированы друг от друга. Имеют доступ к ядру. |

### 1.2. Принципы

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
| 10 | **Полнота контракта доступа** | **Реплика хранит ВСЕ поля контракта доступа (§3.3 ТЗ): `tenant_id`, `section_id`, `author_id`, `or_tags`, `and_tags`. Это позволяет домену-получателю вычислять доступ через `AccessService` по правилам ТЗ RBAC/ABAC** |

### 1.3. Матрица доступа

| Источник → Цель | Ядро | Домен А | Домен Б |
|-----------------|:----:|:-------:|:-------:|
| **Ядро** | ✅ | ❌ | ❌ |
| **Домен А** | ✅ (F-Keys, JOINs) | ✅ (внутри) | ❌ (только реплика) |
| **Домен Б** | ✅ (F-Keys, JOINs) | ❌ (только реплика) | ✅ (внутри) |

---

## 2. Структура проекта

### 2.1. Backend

```
backend/app/
├── main.py                             # FastAPI app, lifespan с запуском репликатора
├── core/                               # ЯДРО (платформа)
│   ├── database.py
│   ├── schemas.py
│   ├── exceptions.py
│   ├── crud/base.py
│   ├── auth/                           # Аутентификация
│   ├── events/                         # ⭐ ИНФРАСТРУКТУРА РЕПЛИКАЦИИ
│   │   ├── models.py                   # CoreOutbox, CoreInbox, CoreReplicationTask, ...
│   │   ├── outbox.py                   # OutboxPublisher
│   │   ├── replicator.py              # Replicator (фоновый процесс)
│   │   └── handlers.py                # Базовый класс ReplicaHandler + реестр
│   ├── tenants/, users/, roles/, sections/, permissions/,
│   ├── doctypes/, domains/, periods/, currencies/
│   └── ...
├── operations/                         # ДОМЕН: Операции (префикс `oper`)
│   ├── __init__.py                     # Публичный интерфейс домена
│   ├── replica/                        # Реплики из ДРУГИХ доменов
│   │   ├── models.py
│   │   ├── schemas.py
│   │   └── handlers.py                 # Обработчики входящих событий
│   ├── goods/, legal_entities/, locations/, persons/,
│   ├── regions/, vat_invoices/, warehouses/, bank_accounts/
│   └── ...
└── {future_domain}/                    # Будущие домены
```

### 2.2. Frontend

```
frontend/src/
├── core/                               # ЯДРО
│   ├── api/generated/
│   ├── tenants/, users/, roles/, ...
├── operations/                         # ДОМЕН: Операции
│   ├── goods/, legal_entities/, ...
├── shared/                             # Общие компоненты (shadcn/ui, ReferenceSelect)
└── lib/                                # Утилиты
```

---

## 3. Соглашения по именованию

### 3.1. Таблицы

| Уровень | Префикс | Пример |
|---------|---------|--------|
| Ядро (бизнес-сущности) | Без префикса | `tenants`, `users`, `roles`, `periods`, `currencies` |
| Ядро (инфраструктура) | `core_` | `core_outbox`, `core_inbox`, `core_replication_tasks`, `core_sequence_counters`, `core_replication_progress` |
| Домен | `{domain}_` | `oper_goods`, `oper_warehouses`, `sales_orders` |
| Реплика между доменами | `{domain}_{source_domain}_{entity}_replica` | `sales_oper_goods_replica` |

### 3.2. Модели SQLAlchemy

```python
# Ядро
class TenantModel(Base):
    __tablename__ = "tenants"

# Домен
class OperGoodsModel(Base):
    __tablename__ = "oper_goods"

# Реплика
class SalesOperGoodsReplicaModel(Base):
    __tablename__ = "sales_oper_goods_replica"
```

### 3.3. Типы событий

Формат: `{домен}.{сущность}.{действие}`

Примеры:
- `operations.goods.created`
- `operations.goods.updated`
- `operations.goods.deleted`
- `operations.stock.movement`
- `sales.orders.state_changed`

---

## 4. Механизм репликации

### 4.1. Общая схема

```
┌─────────────────────────────────────────────────────────────────┐
│  МАСТЕР-ДОМЕН (например, operations)                            │
│                                                                  │
│  1. Бизнес-транзакция (создание товара)                         │
│     ↓ (в той же транзакции)                                     │
│  2. Атомарное увеличение счётчика группы                        │
│     → core_sequence_counters (ordering_key, counter)            │
│     ↓                                                           │
│  3. Запись события в outbox                                     │
│     → core_outbox (event_type, ordering_key, sequence_no, ...)  │
│     ↓                                                           │
│  4. COMMIT (основное изменение + событие + счётчик)             │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  РЕПЛИКАТОР (фоновый процесс)                                    │
│                                                                  │
│  5. Чтение необработанных событий из core_outbox                │
│     ↓                                                           │
│  6. Создание задач для каждого подписанного домена               │
│     → core_replication_tasks (с ordering_key, sequence_no)      │
│     ↓                                                           │
│  7. Пометка события как обработанного                           │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  ПРИМЕНЕНИЕ ЗАДАЧ (параллельные воркеры)                         │
│                                                                  │
│  8. Выборка задач со строгим порядком:                          │
│     WHERE sequence_no = last_applied_sequence + 1               │
│     ↓                                                           │
│  9. Проверка идемпотентности (core_inbox)                       │
│     ↓                                                           │
│ 10. Адвайзорная блокировка по ordering_key                      │
│     → pg_advisory_xact_lock(hashtext(ordering_key))             │
│     ↓                                                           │
│ 11. Применение изменения к реплике (включая контракт доступа)   │
│     ↓                                                           │
│ 12. Обновление прогресса группы                                 │
│     → core_replication_progress                                 │
│     ↓                                                           │
│ 13. Запись в core_inbox (идемпотентность)                       │
│     ↓                                                           │
│ 14. COMMIT                                                      │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2. Ключ упорядочивания (ordering_key)

Все события с одним ключом применяются **строго последовательно**, события с разными ключами — **параллельно**.

| Сценарий | Ключ упорядочивания |
|----------|---------------------|
| Жизненный цикл сущности | `{домен}:{сущность}:{id}` |
| Жизненный цикл заказа | `order:{order_id}` |
| Движения товара на складе | `stock:{warehouse_id}:{goods_id}` |
| Операции по банковскому счёту | `account:{bank_account_id}` |

### 4.3. Номер последовательности (sequence_no)

Монотонно возрастающий номер внутри каждой группы, фиксируется **в момент публикации** (в той же транзакции, что и основное изменение).

Гарантирует, что даже при параллельной публикации двух событий одного ключа порядок определён однозначно.

### 4.4. Строгий порядок применения

Задача может быть применена **только если** её `sequence_no` равен `last_applied_sequence + 1` для данной группы. Задачи с более высокими номерами остаются в статусе `waiting`.

### 4.5. Идемпотентность

Таблица `core_inbox` с уникальным `(event_id, consumer_domain)` гарантирует, что каждое событие применяется каждым доменом ровно один раз, даже при повторной доставке.

### 4.6. Защита от параллельных воркеров

- `pg_advisory_xact_lock(hashtext(ordering_key))` — адвайзорная блокировка на уровне группы
- `FOR UPDATE SKIP LOCKED` — при выборке задач воркерами

### 4.7. Повторные попытки

При ошибке:
- `attempts += 1`
- `status = 'pending'`
- `next_retry_at = now() + 2^attempts секунд` (экспоненциальная задержка, макс. 60 сек)
- При `attempts >= MAX_ATTEMPTS` → `status = 'failed'`

### 4.8. Специфика состояний (конечные автоматы)

Для сущностей с жизненным циклом (заказы) дополнительно проверяется валидность переходов:

```python
ORDER_TRANSITIONS = {
    "draft":     {"created"},
    "created":   {"confirmed", "cancelled"},
    "confirmed": {"shipped", "cancelled"},
    "shipped":   {"closed"},
    "closed":    set(),
    "cancelled": set(),
}
```

При пропуске промежуточного состояния задача переводится в `waiting` (не в `failed`) — ожидается доставка пропущенного события.

### 4.9. Специфика склада (защита от отрицательного остатка)

- `CHECK (quantity >= 0)` на уровне БД
- Строгий порядок по ключу `stock:{warehouse_id}:{goods_id}`
- Застрявшие группы — алерт администратору через 5 минут

### 4.10. Репликация контракта доступа

#### 4.10.1. Обязательность полей доступа в реплике

Если мастер-сущность наследует `DocumentAccessMixin` (ТЗ §3.3), реплика в домене-получателе **ОБЯЗАНА** содержать все 5 полей контракта:

| Поле | Тип | Назначение в домене-получателе |
|------|-----|-------------------------------|
| `tenant_id` | `UUID NOT NULL` | Слой 1: тенантная фильтрация (ШАГ 1 алгоритма) |
| `section_id` | `UUID NOT NULL` | Слой 2: видимость по разделам роли (ШАГ 3) |
| `author_id` | `UUID NOT NULL` | Слой 5: определение уровня «автор» (ШАГ 4) |
| `or_tags` | `VARCHAR(128)[]` | Слой 4: разрешающие теги, ИЛИ (ШАГ 7) |
| `and_tags` | `VARCHAR(128)[]` | Слой 4: обязательные теги, И (ШАГ 7) |

#### 4.10.2. Реплика не наследует миксины как классы

Реплика — это **НЕ документ** в домене-получателе:
- НЕ наследует `DocumentAccessMixin` и `DocumentLifecycleMixin` как классы модели
- НЕ имеет полей жизненного цикла (`doc_status`, `version`, `editing_*`)
- Хранит поля доступа как **обычные колонки таблицы**
- Имеет собственные метаданные синхронизации (`replica_version`, `replica_synced_at`, `is_deleted`)

#### 4.10.3. Ссылки на ядро, а не на домен-источник

Поля `section_id` и `author_id` ссылаются на таблицы **ЯДРА** (`sections`, `users`), которые доступны всем доменам. Внешние ключи на таблицы ядра из реплики **РАЗРЕШЕНЫ** (домен → ядро, матрица доступа §1.3).

#### 4.10.4. Обязательность полей в `payload` события

Мастер-домен при публикации события **ОБЯЗАН** включать в `payload` все поля контракта доступа:

```json
{
    "id": "<aggregate_id>",
    "name": "<название>",
    "tenant_id": "<uuid>",
    "section_id": "<uuid>",
    "author_id": "<uuid>",
    "or_tags": ["тег1", "тег2"],
    "and_tags": ["тег3"],
    "is_deleted": false
}
```

#### 4.10.5. Вычисление доступа к реплике

Домен-получатель вычисляет доступ к записи реплики через `AccessService`, передавая поля реплики как атрибуты документа:

```python
access = await access_service.resolve_access(
    user=user,
    document=ReplicaAccessView(
        tenant_id=replica.tenant_id,
        section_id=replica.section_id,
        author_id=replica.author_id,
        or_tags=replica.or_tags,
        and_tags=replica.and_tags,
        doctype="<код типа мастер-сущности>",
    ),
    now=datetime.now(timezone.utc),
)

if not access.visible:
    # Запись не существует для пользователя (ТЗ §2.3, §2.6)
    raise HTTPException(status_code=404, detail="Не найдено")
```

#### 4.10.6. Обработка мягкого удаления

При получении события с `is_deleted: true` реплика помечается `is_deleted = true`. Записи с `is_deleted = true` не возвращаются в списках и не участвуют в вычислении доступа (аналог `deleted_at IS NULL` для документов).

---

## 5. DDL таблиц репликации (полный)

```sql
-- ═══════════════════════════════════════════════════════════════
-- ИНФРАСТРУКТУРА РЕПЛИКАЦИИ МЕЖДУ ДОМЕНАМИ
-- Ядро (core), префикс core_
-- ═══════════════════════════════════════════════════════════════

-- ============================================================
-- 1. ИСХОДЯЩИЕ СОБЫТИЯ (транзакционный outbox)
-- ============================================================
CREATE TABLE public.core_outbox (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type      VARCHAR(128) NOT NULL,
    source_domain   VARCHAR(64)  NOT NULL,
    aggregate_type  VARCHAR(128) NOT NULL,
    aggregate_id    UUID         NOT NULL,
    payload         JSONB        NOT NULL,
    ordering_key    VARCHAR(255) NOT NULL DEFAULT '',
    sequence_no     BIGINT,
    occurred_at     TIMESTAMPTZ  NOT NULL DEFAULT now(),
    processed       BOOLEAN      NOT NULL DEFAULT false,
    processed_at    TIMESTAMPTZ
);

CREATE INDEX idx_core_outbox_unprocessed
    ON public.core_outbox (processed, occurred_at)
    WHERE processed = false;

CREATE INDEX idx_core_outbox_aggregate
    ON public.core_outbox (aggregate_type, aggregate_id);

CREATE INDEX idx_core_outbox_ordering
    ON public.core_outbox (ordering_key, sequence_no);

COMMENT ON TABLE public.core_outbox IS
    'Транзакционный outbox: события изменения данных в мастер-доменах.';

-- ============================================================
-- 2. СЧЁТЧИКИ ПОСЛЕДОВАТЕЛЬНОСТИ ПО КЛЮЧАМ УПОРЯДОЧИВАНИЯ
-- ============================================================
CREATE TABLE public.core_sequence_counters (
    ordering_key    VARCHAR(255) PRIMARY KEY,
    counter         BIGINT       NOT NULL DEFAULT 0,
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.core_sequence_counters IS
    'Монотонные счётчики последовательности событий по ordering_key.';

-- ============================================================
-- 3. ОБРАБОТАННЫЕ СОБЫТИЯ (идемпотентность)
-- ============================================================
CREATE TABLE public.core_inbox (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id        UUID         NOT NULL,
    consumer_domain VARCHAR(64)  NOT NULL,
    processed_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT uq_core_inbox_event_consumer
        UNIQUE (event_id, consumer_domain)
);

CREATE INDEX idx_core_inbox_event
    ON public.core_inbox (event_id);

CREATE INDEX idx_core_inbox_consumer
    ON public.core_inbox (consumer_domain);

COMMENT ON TABLE public.core_inbox IS
    'Подтверждения обработки событий для идемпотентности репликации.';

-- ============================================================
-- 4. ОЧЕРЕДЬ ЗАДАЧ НА СИНХРОНИЗАЦИЮ
-- ============================================================
CREATE TABLE public.core_replication_tasks (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id        UUID         NOT NULL,
    target_domain   VARCHAR(64)  NOT NULL,
    target_table    VARCHAR(128) NOT NULL,
    aggregate_type  VARCHAR(128) NOT NULL,
    operation       VARCHAR(32)  NOT NULL,
    payload         JSONB        NOT NULL,
    ordering_key    VARCHAR(255) NOT NULL DEFAULT '',
    sequence_no     BIGINT       NOT NULL DEFAULT 0,
    status          VARCHAR(32)  NOT NULL DEFAULT 'pending',
    attempts        INTEGER      NOT NULL DEFAULT 0,
    last_error      TEXT,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    processed_at    TIMESTAMPTZ,
    next_retry_at   TIMESTAMPTZ,
    CONSTRAINT fk_core_replication_tasks_outbox
        FOREIGN KEY (event_id) REFERENCES public.core_outbox(id),
    CONSTRAINT chk_core_replication_tasks_status
        CHECK (status IN ('pending', 'processing', 'waiting', 'completed', 'failed')),
    CONSTRAINT chk_core_replication_tasks_operation
        CHECK (operation IN ('upsert', 'delete'))
);

CREATE INDEX idx_core_replication_tasks_pending
    ON public.core_replication_tasks (status, next_retry_at)
    WHERE status IN ('pending', 'waiting');

CREATE INDEX idx_core_replication_tasks_event
    ON public.core_replication_tasks (event_id);

CREATE INDEX idx_core_replication_tasks_group
    ON public.core_replication_tasks (target_domain, ordering_key, sequence_no);

COMMENT ON TABLE public.core_replication_tasks IS
    'Очередь задач репликации реплик в целевых доменах.';

-- ============================================================
-- 5. ПРОГРЕСС ПРИМЕНЕНИЯ ПО ГРУППАМ
-- ============================================================
CREATE TABLE public.core_replication_progress (
    consumer_domain       VARCHAR(64)  NOT NULL,
    ordering_key          VARCHAR(255) NOT NULL,
    last_applied_sequence BIGINT       NOT NULL DEFAULT 0,
    updated_at            TIMESTAMPTZ  NOT NULL DEFAULT now(),
    PRIMARY KEY (consumer_domain, ordering_key)
);

COMMENT ON TABLE public.core_replication_progress IS
    'Прогресс применения событий по группам (ordering_key) в каждом домене.';

-- ============================================================
-- 6. МЕТРИКИ РЕПЛИКАЦИИ (для мониторинга)
-- ============================================================
CREATE TABLE public.core_replication_metrics (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    measured_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    outbox_pending  INTEGER     NOT NULL DEFAULT 0,
    tasks_pending   INTEGER     NOT NULL DEFAULT 0,
    tasks_waiting   INTEGER     NOT NULL DEFAULT 0,
    tasks_failed    INTEGER     NOT NULL DEFAULT 0,
    avg_latency_ms  INTEGER
);

CREATE INDEX idx_core_replication_metrics_measured
    ON public.core_replication_metrics (measured_at DESC);

COMMENT ON TABLE public.core_replication_metrics IS
    'Периодические снимки состояния репликации для мониторинга.';
```

### 5.1. Пример таблицы реплики в домене-получателе

```sql
-- Домен sales, реплика товаров из домена operations
-- ✅ ПОЛНЫЙ КОНТРАКТ ДОСТУПА в реплике (раздел 4.10)
CREATE TABLE public.sales_oper_goods_replica (
    -- ID оригинала из oper_goods (БЕЗ ForeignKey на чужой домен!)
    goods_id          UUID PRIMARY KEY,

    -- Скопированные бизнес-данные
    name              VARCHAR(255) NOT NULL,
    code              VARCHAR(64),

    -- ✅ КОНТРАКТ ДОСТУПА (§3.3) — все 5 полей обязательны
    -- Ссылки на таблицы ЯДРА (разрешены матрицей доступа §1.3)
    tenant_id         UUID         NOT NULL REFERENCES public.tenants(id),
    section_id        UUID         NOT NULL REFERENCES public.sections(id),
    author_id         UUID         NOT NULL REFERENCES public.users(id),
    or_tags           VARCHAR(128)[],
    and_tags          VARCHAR(128)[],

    -- Метаданные синхронизации
    replica_version   INTEGER      NOT NULL DEFAULT 1,
    replica_synced_at TIMESTAMPTZ  NOT NULL DEFAULT now(),
    is_deleted        BOOLEAN      NOT NULL DEFAULT false
);

-- Индексы для вычисления доступа и производительности
CREATE INDEX idx_sales_oper_goods_replica_tenant
    ON public.sales_oper_goods_replica (tenant_id);
CREATE INDEX idx_sales_oper_goods_replica_section
    ON public.sales_oper_goods_replica (section_id);
CREATE INDEX idx_sales_oper_goods_replica_or_tags
    ON public.sales_oper_goods_replica USING GIN (or_tags);
CREATE INDEX idx_sales_oper_goods_replica_and_tags
    ON public.sales_oper_goods_replica USING GIN (and_tags);
CREATE INDEX idx_sales_oper_goods_replica_active
    ON public.sales_oper_goods_replica (tenant_id)
    WHERE is_deleted = false;

COMMENT ON TABLE public.sales_oper_goods_replica IS
    'Реплика товаров из домена operations. '
    'Содержит полный контракт доступа (§3.3) для вычисления '
    'видимости и уровня через AccessService.';
```

### 5.2. Пример таблицы склада (с CHECK-ограничением)

```sql
CREATE TABLE public.oper_stock (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID         NOT NULL REFERENCES public.tenants(id),
    warehouse_id    UUID         NOT NULL REFERENCES public.oper_warehouses(id),
    goods_id        UUID         NOT NULL REFERENCES public.oper_goods(id),
    quantity        NUMERIC(18,4) NOT NULL DEFAULT 0,
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    UNIQUE (warehouse_id, goods_id),
    CONSTRAINT chk_oper_stock_non_negative CHECK (quantity >= 0)
);
```

---

## 6. Полный код репликатора на Python

### 6.1. `backend/app/core/events/models.py` — Модели инфраструктуры

```python
"""Модели инфраструктуры репликации между доменами."""
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CoreOutboxModel(Base):
    """Исходящие события (транзакционный outbox)."""

    __tablename__ = "core_outbox"
    __table_args__ = {"schema": "public"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuid_generate_v4()"),
    )
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    source_domain: Mapped[str] = mapped_column(String(64), nullable=False)
    aggregate_type: Mapped[str] = mapped_column(String(128), nullable=False)
    aggregate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    ordering_key: Mapped[str] = mapped_column(
        String(255), nullable=False, server_default=text("''")
    )
    sequence_no: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    processed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class CoreSequenceCounterModel(Base):
    """Счётчики последовательности по ключам упорядочивания."""

    __tablename__ = "core_sequence_counters"
    __table_args__ = {"schema": "public"}

    ordering_key: Mapped[str] = mapped_column(String(255), primary_key=True)
    counter: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default=text("0")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )


class CoreInboxModel(Base):
    """Обработанные события (идемпотентность)."""

    __tablename__ = "core_inbox"
    __table_args__ = {"schema": "public"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuid_generate_v4()"),
    )
    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    consumer_domain: Mapped[str] = mapped_column(String(64), nullable=False)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )


class CoreReplicationTaskModel(Base):
    """Задачи репликации."""

    __tablename__ = "core_replication_tasks"
    __table_args__ = {"schema": "public"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuid_generate_v4()"),
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.core_outbox.id"),
        nullable=False,
    )
    target_domain: Mapped[str] = mapped_column(String(64), nullable=False)
    target_table: Mapped[str] = mapped_column(String(128), nullable=False)
    aggregate_type: Mapped[str] = mapped_column(String(128), nullable=False)
    operation: Mapped[str] = mapped_column(String(32), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    ordering_key: Mapped[str] = mapped_column(
        String(255), nullable=False, server_default=text("''")
    )
    sequence_no: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default=text("0")
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default=text("'pending'")
    )
    attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    next_retry_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class CoreReplicationProgressModel(Base):
    """Прогресс применения событий по группам."""

    __tablename__ = "core_replication_progress"
    __table_args__ = {"schema": "public"}

    consumer_domain: Mapped[str] = mapped_column(String(64), primary_key=True)
    ordering_key: Mapped[str] = mapped_column(String(255), primary_key=True)
    last_applied_sequence: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default=text("0")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
```

### 6.2. `backend/app/core/events/outbox.py` — Публикация событий

```python
"""Публикация событий в транзакционный outbox."""
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import insert, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events.models import CoreOutboxModel


class OutboxPublisher:
    """
    Публикация событий в транзакционный outbox.
    Вызывать в той же транзакции, что и основное изменение.
    Commit выполняется в роутере (Бэкенд Правило №31).

    ⚠️ ВАЖНО (раздел 4.10.4): если мастер-сущность наследует
    DocumentAccessMixin, payload ОБЯЗАН содержать все 5 полей
    контракта доступа: tenant_id, section_id, author_id,
    or_tags, and_tags.
    """

    async def publish(
        self,
        db: AsyncSession,
        *,
        event_type: str,
        source_domain: str,
        aggregate_type: str,
        aggregate_id: uuid.UUID,
        payload: dict[str, Any],
        ordering_key: str | None = None,
    ) -> None:
        """
        Публикация события.

        Если указан ordering_key — атомарно увеличивает счётчик
        и присваивает монотонный sequence_no.
        """
        sequence_no: int | None = None

        if ordering_key:
            seq_stmt = text("""
                INSERT INTO core_sequence_counters (ordering_key, counter, updated_at)
                VALUES (:key, 1, now())
                ON CONFLICT (ordering_key)
                DO UPDATE SET counter = core_sequence_counters.counter + 1,
                              updated_at = now()
                RETURNING counter
            """)
            result = await db.execute(seq_stmt, {"key": ordering_key})
            sequence_no = result.scalar_one()

        stmt = insert(CoreOutboxModel).values(
            event_type=event_type,
            source_domain=source_domain,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            payload=payload,
            ordering_key=ordering_key or "",
            sequence_no=sequence_no,
            occurred_at=datetime.now(timezone.utc),
            processed=False,
        )
        await db.execute(stmt)


outbox = OutboxPublisher()
```

### 6.3. `backend/app/core/events/handlers.py` — Реестр обработчиков

```python
"""Реестр обработчиков репликации и базовый класс."""
from typing import Any, Protocol

from sqlalchemy.ext.asyncio import AsyncSession


class ReplicaHandler(Protocol):
    """Протокол обработчика репликации для домена-получателя."""

    def get_target_table(self) -> str:
        """Имя таблицы реплики в целевом домене."""
        ...

    def get_target_domain(self) -> str:
        """Имя целевого домена."""
        ...

    async def apply(
        self,
        db: AsyncSession,
        payload: dict[str, Any],
        operation: str,
    ) -> None:
        """Применить изменение к реплике."""
        ...


# Глобальный реестр обработчиков
# Ключ: (target_domain, aggregate_type) → ReplicaHandler
REPLICATION_HANDLERS: dict[tuple[str, str], ReplicaHandler] = {}


def register_handler(
    target_domain: str,
    aggregate_type: str,
    handler: ReplicaHandler,
) -> None:
    """Зарегистрировать обработчик репликации."""
    key = (target_domain, aggregate_type)
    if key in REPLICATION_HANDLERS:
        raise ValueError(f"Обработчик для {key} уже зарегистрирован")
    REPLICATION_HANDLERS[key] = handler


def get_handler(
    target_domain: str,
    aggregate_type: str,
) -> ReplicaHandler | None:
    """Получить обработчик по ключу."""
    return REPLICATION_HANDLERS.get((target_domain, aggregate_type))


def get_subscribed_domains(aggregate_type: str) -> list[str]:
    """Получить список доменов, подписанных на данный aggregate_type."""
    return [
        domain
        for (domain, agg_type) in REPLICATION_HANDLERS.keys()
        if agg_type == aggregate_type
    ]


class SequenceGapError(Exception):
    """Обнаружен пропуск в последовательности событий (для конечных автоматов)."""
    pass
```

### 6.4. `backend/app/core/events/replicator.py` — Фоновый процесс

```python
"""
Фоновый процесс репликации между доменами.
Запускается через lifespan в main.py.
Читает core_outbox, создаёт задачи, применяет их со строгим порядком
внутри групп (ordering_key).
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session
from app.core.events.models import (
    CoreInboxModel,
    CoreOutboxModel,
    CoreReplicationProgressModel,
    CoreReplicationTaskModel,
)
from app.core.events.handlers import (
    REPLICATION_HANDLERS,
    SequenceGapError,
    get_handler,
    get_subscribed_domains,
)

logger = logging.getLogger(__name__)


class Replicator:
    """Фоновый процесс репликации."""

    POLL_INTERVAL: float = 2.0      # Секунды между опросами
    BATCH_SIZE: int = 50            # Размер батча событий/задач
    MAX_ATTEMPTS: int = 5           # Максимум попыток обработки задачи
    MAX_RETRY_DELAY: int = 60       # Максимальная задержка (секунды)

    async def run(self) -> None:
        """Главный цикл репликатора."""
        logger.info("[Replicator] Запуск фонового процесса репликации")
        while True:
            try:
                await self._process_outbox()
                await self._process_tasks()
            except asyncio.CancelledError:
                logger.info("[Replicator] Остановка по запросу")
                raise
            except Exception as e:
                logger.exception("[Replicator] Ошибка цикла: %s", str(e))
            await asyncio.sleep(self.POLL_INTERVAL)

    # ================================================================
    # ФАЗА 1: Чтение outbox → создание задач
    # ================================================================

    async def _process_outbox(self) -> None:
        """Обработка необработанных событий из core_outbox."""
        async with async_session() as db:
            stmt = (
                select(CoreOutboxModel)
                .where(CoreOutboxModel.processed == False)  # noqa: E712
                .order_by(CoreOutboxModel.occurred_at.asc())
                .limit(self.BATCH_SIZE)
            )
            result = await db.execute(stmt)
            events = list(result.scalars().all())

            if not events:
                return

            logger.info("[Replicator] Обработка %d событий", len(events))

            for event in events:
                await self._create_replication_tasks(db, event)
                event.processed = True
                event.processed_at = datetime.now(timezone.utc)

            await db.commit()

    async def _create_replication_tasks(
        self,
        db: AsyncSession,
        event: CoreOutboxModel,
    ) -> None:
        """Создание задач репликации для подписанных доменов."""
        subscribed_domains = get_subscribed_domains(event.aggregate_type)

        for target_domain in subscribed_domains:
            # Проверка идемпотентности
            inbox_stmt = select(CoreInboxModel).where(
                CoreInboxModel.event_id == event.id,
                CoreInboxModel.consumer_domain == target_domain,
            )
            inbox_result = await db.execute(inbox_stmt)
            if inbox_result.scalar_one_or_none() is not None:
                continue  # Уже обработано этим доменом

            handler = get_handler(target_domain, event.aggregate_type)
            if handler is None:
                continue

            # Проверка, что задача ещё не создана
            existing_stmt = select(CoreReplicationTaskModel).where(
                CoreReplicationTaskModel.event_id == event.id,
                CoreReplicationTaskModel.target_domain == target_domain,
            )
            existing_result = await db.execute(existing_stmt)
            if existing_result.scalar_one_or_none() is not None:
                continue

            is_deleted = event.payload.get("is_deleted", False)
            operation = "delete" if is_deleted else "upsert"

            task = CoreReplicationTaskModel(
                event_id=event.id,
                target_domain=target_domain,
                target_table=handler.get_target_table(),
                aggregate_type=event.aggregate_type,
                operation=operation,
                payload=event.payload,
                ordering_key=event.ordering_key or "",
                sequence_no=event.sequence_no or 0,
                status="pending",
            )
            db.add(task)

    # ================================================================
    # ФАЗА 2: Применение задач со строгим порядком
    # ================================================================

    async def _process_tasks(self) -> None:
        """Применение задач из очереди со строгим порядком."""
        async with async_session() as db:
            stmt = text("""
                SELECT t.*
                FROM core_replication_tasks t
                LEFT JOIN core_replication_progress p
                    ON  p.consumer_domain = t.target_domain
                    AND p.ordering_key    = t.ordering_key
                WHERE t.status IN ('pending', 'waiting')
                  AND (t.next_retry_at IS NULL OR t.next_retry_at <= now())
                  AND (
                      (p.last_applied_sequence IS NULL AND t.sequence_no <= 1)
                      OR
                      (p.last_applied_sequence IS NOT NULL
                       AND t.sequence_no = p.last_applied_sequence + 1)
                  )
                ORDER BY t.created_at ASC
                LIMIT :batch_size
                FOR UPDATE SKIP LOCKED
            """)
            result = await db.execute(stmt, {"batch_size": self.BATCH_SIZE})
            rows = result.fetchall()

            if not rows:
                await self._mark_waiting_tasks(db)
                return

            for row in rows:
                task_id = row.id
                await self._apply_task_by_id(db, task_id)

            await db.commit()

    async def _mark_waiting_tasks(self, db: AsyncSession) -> None:
        """Пометить задачи как waiting, если их предыдущая ещё не применена."""
        stmt = text("""
            UPDATE core_replication_tasks t
            SET status = 'waiting',
                next_retry_at = now() + interval '30 seconds'
            WHERE t.status = 'pending'
              AND t.created_at < now() - interval '10 seconds'
              AND NOT EXISTS (
                  SELECT 1 FROM core_replication_progress p
                  WHERE p.consumer_domain = t.target_domain
                    AND p.ordering_key = t.ordering_key
                    AND t.sequence_no = p.last_applied_sequence + 1
              )
              AND NOT EXISTS (
                  SELECT 1 FROM core_replication_progress p
                  WHERE p.consumer_domain = t.target_domain
                    AND p.ordering_key = t.ordering_key
                    AND p.last_applied_sequence IS NULL
                    AND t.sequence_no <= 1
              )
        """)
        await db.execute(stmt)

    async def _apply_task_by_id(
        self,
        db: AsyncSession,
        task_id: Any,
    ) -> None:
        """Применение одной задачи по ID."""
        task = await db.get(CoreReplicationTaskModel, task_id)
        if task is None:
            return

        handler = get_handler(task.target_domain, task.aggregate_type)
        if handler is None:
            logger.warning(
                "[Replicator] Обработчик не найден для (%s, %s)",
                task.target_domain, task.aggregate_type,
            )
            task.status = "failed"
            task.last_error = "Handler not found"
            return

        # Адвайзорная блокировка по ключу группы
        if task.ordering_key:
            lock_stmt = text("SELECT pg_advisory_xact_lock(hashtext(:key))")
            await db.execute(lock_stmt, {"key": task.ordering_key})

        # Повторная проверка прогресса под блокировкой
        progress_stmt = select(CoreReplicationProgressModel).where(
            CoreReplicationProgressModel.consumer_domain == task.target_domain,
            CoreReplicationProgressModel.ordering_key == task.ordering_key,
        )
        progress_result = await db.execute(progress_stmt)
        progress = progress_result.scalar_one_or_none()

        last_applied = progress.last_applied_sequence if progress else 0
        expected_seq = last_applied + 1

        # Идемпотентность: задача уже применена
        if task.sequence_no < expected_seq:
            task.status = "completed"
            task.processed_at = datetime.now(timezone.utc)
            return

        # Задача ещё не готова (предыдущая не применена)
        if task.sequence_no > expected_seq:
            task.status = "waiting"
            task.next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=30)
            return

        # Применяем
        task.status = "processing"
        task.attempts += 1

        try:
            await handler.apply(db, task.payload, task.operation)

            # Обновляем/создаём прогресс группы
            if progress is None:
                progress = CoreReplicationProgressModel(
                    consumer_domain=task.target_domain,
                    ordering_key=task.ordering_key,
                    last_applied_sequence=task.sequence_no,
                    updated_at=datetime.now(timezone.utc),
                )
                db.add(progress)
            else:
                progress.last_applied_sequence = task.sequence_no
                progress.updated_at = datetime.now(timezone.utc)

            # Записываем в inbox (идемпотентность)
            inbox = CoreInboxModel(
                event_id=task.event_id,
                consumer_domain=task.target_domain,
                processed_at=datetime.now(timezone.utc),
            )
            db.add(inbox)

            task.status = "completed"
            task.processed_at = datetime.now(timezone.utc)
            task.last_error = None

            logger.info(
                "[Replicator] ✓ %s → %s (seq=%d)",
                task.target_table, task.operation, task.sequence_no,
            )

        except SequenceGapError as e:
            task.last_error = str(e)
            task.status = "waiting"
            task.next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=30)
            logger.warning("[Replicator] SequenceGap: %s", str(e))

        except Exception as e:
            task.last_error = str(e)
            logger.error(
                "[Replicator] Ошибка применения задачи %s: %s",
                task.id, str(e),
            )

            if task.attempts >= self.MAX_ATTEMPTS:
                task.status = "failed"
                logger.error(
                    "[Replicator] Задача %s провалилась после %d попыток",
                    task.id, task.attempts,
                )
            else:
                task.status = "pending"
                retry_delay = min(self.MAX_RETRY_DELAY, 2 ** task.attempts)
                task.next_retry_at = datetime.now(timezone.utc) + timedelta(
                    seconds=retry_delay
                )


replicator = Replicator()
```

### 6.5. `backend/app/main.py` — Запуск репликатора

```python
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.events.replicator import replicator

# Импорт модулей с обработчиками для регистрации
import app.operations.replica.handlers  # noqa: F401
import app.sales.replica.handlers       # noqa: F401
import app.business_partners.replica.handlers  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Жизненный цикл приложения."""
    replicator_task = asyncio.create_task(replicator.run())
    try:
        yield
    finally:
        replicator_task.cancel()
        try:
            await replicator_task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="Cool ERP", lifespan=lifespan)
```

---

## 7. Примеры сценариев

### 7.1. Создание товара в домене Operations

```python
# backend/app/operations/goods/service.py
from app.core.events.outbox import outbox


class GoodsService:
    async def create_goods(
        self,
        db: AsyncSession,
        goods_in: OperGoodsCreateSchema,
    ) -> OperGoodsModel:
        new_goods = await crud_goods.create(db, obj_in=goods_in)

        await outbox.publish(
            db,
            event_type="operations.goods.created",
            source_domain="operations",
            aggregate_type="oper_goods",
            aggregate_id=new_goods.id,
            payload={
                # Бизнес-данные
                "id": str(new_goods.id),
                "name": new_goods.name,
                "code": new_goods.code,
                # ✅ КОНТРАКТ ДОСТУПА (§3.3) — обязателен в каждом событии
                "tenant_id": str(new_goods.tenant_id),
                "section_id": str(new_goods.section_id),
                "author_id": str(new_goods.author_id),
                "or_tags": list(new_goods.or_tags or []),
                "and_tags": list(new_goods.and_tags or []),
                "is_deleted": False,
            },
            ordering_key=f"operations:oper_goods:{new_goods.id}",
        )
        # Commit в роутере (Бэкенд Правило №31)
        return new_goods
```

### 7.2. Складская операция

```python
await outbox.publish(
    db,
    event_type="operations.stock.movement",
    source_domain="operations",
    aggregate_type="oper_stock",
    aggregate_id=movement.id,
    payload={
        "warehouse_id": str(movement.warehouse_id),
        "goods_id": str(movement.goods_id),
        "delta": float(movement.quantity_delta),
        "movement_type": movement.movement_type,
        "tenant_id": str(movement.tenant_id),
        "section_id": str(movement.section_id),
        "author_id": str(movement.author_id),
        "or_tags": list(movement.or_tags or []),
        "and_tags": list(movement.and_tags or []),
    },
    ordering_key=f"stock:{movement.warehouse_id}:{movement.goods_id}",
)
```

### 7.3. Смена состояния заказа (конечный автомат)

```python
ORDER_TRANSITIONS = {
    "draft":     {"created"},
    "created":   {"confirmed", "cancelled"},
    "confirmed": {"shipped", "cancelled"},
    "shipped":   {"closed"},
    "closed":    set(),
    "cancelled": set(),
}


class OrderStatusHandler:
    async def apply(self, db, payload, operation):
        order_id = payload["order_id"]
        new_status = payload["status"]

        replica = await db.get(SalesOrdersReplicaModel, order_id)
        current = replica.status if replica else "draft"

        # Идемпотентность
        if current == new_status:
            return

        # Валидность перехода
        if new_status not in ORDER_TRANSITIONS.get(current, set()):
            # Пропуск промежуточного состояния → ждём
            raise SequenceGapError(
                f"Недопустимый переход {current} → {new_status}"
            )

        replica.status = new_status
        replica.replica_version += 1
```

### 7.4. Обработчик реплики товаров (с контрактом доступа)

```python
# backend/app/sales/replica/handlers.py
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events.handlers import register_handler
from app.sales.replica.models import SalesOperGoodsReplicaModel


class OperGoodsReplicaHandler:
    """
    Обработчик репликации товаров из домена operations в домен sales.
    Применяет бизнес-данные И полный контракт доступа (§4.10).
    """

    def get_target_table(self) -> str:
        return "sales_oper_goods_replica"

    def get_target_domain(self) -> str:
        return "sales"

    async def apply(
        self,
        db: AsyncSession,
        payload: dict[str, Any],
        operation: str,
    ) -> None:
        goods_id = payload["id"]

        stmt = select(SalesOperGoodsReplicaModel).where(
            SalesOperGoodsReplicaModel.goods_id == goods_id
        )
        replica = (await db.execute(stmt)).scalar_one_or_none()

        if operation == "delete":
            # Мягкое удаление реплики
            if replica is not None:
                replica.is_deleted = True
                replica.replica_version += 1
                replica.replica_synced_at = datetime.now(timezone.utc)
            return

        # Upsert реплики с полным контрактом доступа
        if replica is None:
            replica = SalesOperGoodsReplicaModel(
                goods_id=goods_id,
                name=payload["name"],
                code=payload.get("code"),
                # ✅ Контракт доступа (§3.3) — все 5 полей
                tenant_id=payload["tenant_id"],
                section_id=payload["section_id"],
                author_id=payload["author_id"],
                or_tags=payload.get("or_tags"),
                and_tags=payload.get("and_tags"),
            )
            db.add(replica)
        else:
            replica.name = payload["name"]
            replica.code = payload.get("code")
            # ✅ Контракт доступа обновляется при каждом событии
            replica.tenant_id = payload["tenant_id"]
            replica.section_id = payload["section_id"]
            replica.author_id = payload["author_id"]
            replica.or_tags = payload.get("or_tags")
            replica.and_tags = payload.get("and_tags")
            replica.is_deleted = payload.get("is_deleted", False)
            replica.replica_version += 1
            replica.replica_synced_at = datetime.now(timezone.utc)


# Регистрация при импорте модуля
register_handler(
    target_domain="sales",
    aggregate_type="oper_goods",
    handler=OperGoodsReplicaHandler(),
)
```

### 7.5. Модель реплики с контрактом доступа

```python
# backend/app/sales/replica/models.py
"""Реплики из других доменов для домена sales.

✅ Реплика хранит ПОЛНЫЙ КОНТРАКТ ДОСТУПА (§3.3):
   все 5 полей для вычисления видимости и уровня через
   AccessService по правилам ТЗ RBAC/ABAC.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SalesOperGoodsReplicaModel(Base):
    """
    Реплика товаров из домена operations.

    НЕ наследует миксины документов как классы модели —
    реплика не является документом в своём домене.
    Однако хранит ВСЕ поля контракта доступа как обычные колонки.
    """

    __tablename__ = "sales_oper_goods_replica"
    __table_args__ = {"schema": "public"}

    # ID оригинала из домена operations
    # ⚠️ БЕЗ ForeignKey на чужой домен — изоляция доменов
    goods_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
    )

    # Бизнес-данные
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # ✅ КОНТРАКТ ДОСТУПА (§3.3) — все 5 полей
    # Ссылки на таблицы ЯДРА (разрешены матрицей доступа)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.tenants.id"),
        nullable=False,
        index=True,
    )
    section_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.sections.id"),
        nullable=False,
        index=True,
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.users.id"),
        nullable=False,
    )
    or_tags: Mapped[list[str] | None] = mapped_column(
        ARRAY(String(128)),
        nullable=True,
    )
    and_tags: Mapped[list[str] | None] = mapped_column(
        ARRAY(String(128)),
        nullable=True,
    )

    # Метаданные синхронизации
    replica_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default=text("1"),
    )
    replica_synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
```

### 7.6. Вычисление доступа к реплике в домене-получателе

```python
# backend/app/sales/services.py (фрагмент)
from datetime import datetime, timezone


async def get_goods_for_user(
    db: AsyncSession,
    user: UserModel,
    goods_id: uuid.UUID,
) -> SalesOperGoodsReplicaModel:
    """
    Получение товара с проверкой доступа по контракту реплики.
    """
    replica = await crud_goods_replica.get_by_id(db, goods_id=goods_id)
    if replica is None or replica.is_deleted:
        raise HTTPException(status_code=404, detail="Товар не найден")

    # ✅ Вычисление доступа через AccessService по полям реплики
    access = await access_service.resolve_access(
        user=user,
        document=ReplicaAccessView(
            tenant_id=replica.tenant_id,
            section_id=replica.section_id,
            author_id=replica.author_id,
            or_tags=replica.or_tags,
            and_tags=replica.and_tags,
            doctype="oper_goods",
        ),
        now=datetime.now(timezone.utc),
    )

    # ТЗ §2.3, §2.6: нет права на чтение ⇒ запись не существует
    if not access.visible:
        raise HTTPException(status_code=404, detail="Товар не найден")

    # ТЗ §5.4: право на чтение, но недостаточный уровень → только чтение
    # (обрабатывается на фронтенде через поле уровня)

    return replica
```

---

## 8. Мониторинг

### 8.1. Полезные SQL-запросы

```sql
-- Количество необработанных событий
SELECT COUNT(*) AS pending_events
FROM core_outbox
WHERE processed = false;

-- Задачи с ошибками (требуют вмешательства)
SELECT id, target_table, ordering_key, attempts, last_error, created_at
FROM core_replication_tasks
WHERE status = 'failed'
ORDER BY created_at DESC
LIMIT 20;

-- Застрявшие группы склада (старше 5 минут)
SELECT ordering_key,
       MIN(created_at) AS oldest_pending,
       COUNT(*) AS pending_count
FROM core_replication_tasks
WHERE ordering_key LIKE 'stock:%'
  AND status IN ('pending', 'waiting')
GROUP BY ordering_key
HAVING MIN(created_at) < now() - interval '5 minutes';

-- Средняя задержка репликации за последний час
SELECT
    AVG(EXTRACT(EPOCH FROM (t.processed_at - o.occurred_at))) * 1000
        AS avg_latency_ms
FROM core_replication_tasks t
JOIN core_outbox o ON o.id = t.event_id
WHERE t.status = 'completed'
  AND t.processed_at > now() - interval '1 hour';

-- Глубина очередей по группам
SELECT ordering_key, COUNT(*) AS depth
FROM core_replication_tasks
WHERE status IN ('pending', 'waiting')
GROUP BY ordering_key
ORDER BY depth DESC
LIMIT 20;

-- Очистка старых данных (ежедневно по cron)
DELETE FROM core_outbox
WHERE processed = true
  AND processed_at < now() - interval '30 days';

DELETE FROM core_inbox
WHERE processed_at < now() - interval '30 days';
```

### 8.2. Ключевые метрики

| Метрика | Порог алерта | Действие |
|---------|:---:|----------|
| `outbox_pending` | > 1000 | Проверить репликатор |
| `tasks_failed` | > 0 | Разбор ошибок |
| `avg_latency_ms` | > 5000 | Проверить нагрузку БД |
| Застрявшие `stock:*` | > 5 мин | Ручной разбор |
| `waiting` дольше часа | 1 | Пропуск события — вмешательство |

---

## 9. Соответствие правилам проекта

| Правило | Соблюдение |
|---------|------------|
| **Бэкенд №1** | `@property` для вычисляемых полей, `lazy="selectin"` |
| **Бэкенд №26** | Мульти-арендность через фильтрацию `tenant_id` |
| **Бэкенд №28** | `{"schema": "public"}`, именованные ограничения |
| **Бэкенд №31** | `flush` в CRUD, `commit` в роутере |
| **Бэкенд №40** | Двойные блокировки (оптимистическая + пессимистическая) |
| **Бэкенд №44** | Строгая типизация `ColumnElement[Sequence[str]]` для массивов |
| **ТЗ §3.3** | **Контракт атрибутов доступа реплицируется в полном объёме (5 полей)** |
| **ТЗ RBAC/ABAC §8** | **`AccessService` домена-получателя вычисляет доступ по полям реплики** |
| **ТЗ §6** | **Тег-проверка выполняется по `or_tags`/`and_tags` реплики** |
| **ТЗ §12.2** | Аудит операций с данными |

---

## 10. Интервал опроса и возможность подписки

### 10.1. Где определяется интервал опроса

Интервал опроса задаётся в классе `Replicator` (`backend/app/core/events/replicator.py`) как константа класса:

```python
class Replicator:
    POLL_INTERVAL: float = 2.0      # ← Интервал опроса (секунды)
    BATCH_SIZE: int = 50            # Размер батча событий/задач
    MAX_ATTEMPTS: int = 5           # Максимум попыток обработки задачи
    MAX_RETRY_DELAY: int = 60       # Максимальная задержка повторной попытки

    async def run(self) -> None:
        while True:
            try:
                await self._process_outbox()
                await self._process_tasks()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.exception("[Replicator] Ошибка цикла: %s", str(e))
            await asyncio.sleep(self.POLL_INTERVAL)
```

| Параметр | Где задан | Назначение | Типичные значения |
|----------|-----------|------------|-------------------|
| `POLL_INTERVAL` | `Replicator.POLL_INTERVAL` | Пауза между циклами опроса | 0.5–5 секунд |
| `BATCH_SIZE` | `Replicator.BATCH_SIZE` | Сколько событий за один цикл | 10–100 |
| `MAX_ATTEMPTS` | `Replicator.MAX_ATTEMPTS` | Попыток до статуса `failed` | 3–10 |
| `MAX_RETRY_DELAY` | `Replicator.MAX_RETRY_DELAY` | Максимум экспоненциальной задержки | 30–120 секунд |

### 10.2. Возможность подписки на события

В текущей архитектуре — только поллинг (активный опрос таблицы `core_outbox`). Подписка через `LISTEN/NOTIFY` может быть добавлена как расширение.

| Аспект | Поллинг (текущий) | Подписка | Гибрид |
|--------|:---:|:---:|:---:|
| Задержка репликации | до `POLL_INTERVAL` | ~10–50 мс | ~10–50 мс |
| Гарантированная доставка | ✅ | ❌ | ✅ |
| Работа после перезапуска | ✅ | ⚠️ Требует переподключения | ✅ |
| Нагрузка на БД | Постоянный опрос | Минимальная | Минимальная |
| Сложность реализации | Низкая | Средняя | Высосокая |

**Рекомендация:** для модульного монолита с задержкой 1–2 секунды оставить поллинг. При переходе к распределённым доменам — гибридный подход (подписка + страховочный поллинг).

---

## 11. Чек-лист применения

### При создании новой реплики

- [ ] Таблица реплики содержит все 5 полей контракта доступа (`tenant_id`, `section_id`, `author_id`, `or_tags`, `and_tags`)
- [ ] Поля `section_id` и `author_id` имеют F-Keys на таблицы ядра (`sections`, `users`)
- [ ] Поле `tenant_id` имеет F-Key на таблицу ядра (`tenants`)
- [ ] Созданы индексы: на `tenant_id`, `section_id`, GIN на `or_tags`, GIN на `and_tags`, частичный на `is_deleted = false`
- [ ] Реплика НЕ наследует миксины документов как классы модели
- [ ] Обработчик репликации копирует все 5 полей контракта при upsert
- [ ] Обработчик зарегистрирован через `register_handler()`
- [ ] Импорт обработчиков добавлен в `main.py`

### При публикации событий в мастер-домене

- [ ] `payload` содержит все 5 полей контракта доступа
- [ ] Теги передаются как `list(...)` (не `None`, если поле пустое)
- [ ] `ordering_key` задан для сущностей, где важен порядок
- [ ] Событие публикуется в той же транзакции, что и основное изменение
- [ ] При удалении публикуется событие с `is_deleted: true`

### При использовании реплики в домене-получателе

- [ ] Чтение реплики фильтрует `is_deleted = false`
- [ ] Доступ вычисляется через `AccessService.resolve_access()` с полями реплики
- [ ] Записи без права на чтение не возвращаются в списках (ТЗ §2.3, §2.6)
- [ ] Недостаточный уровень при наличии права на чтение → режим «только чтение» (ТЗ §5.4)

---

**Конец документа.** Данный документ версии 1.1 является единственным источником истины по архитектуре модульного монолита и механизму репликации между доменами. Любое отклонение подлежит исправлению при код-ревью.