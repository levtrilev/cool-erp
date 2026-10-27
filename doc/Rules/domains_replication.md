# Техническое задание: Архитектура модульного монолита с механизмом репликации между доменами

**Версия:** 1.0  
**Дата:** 27 октября 2026  
**Проект:** Cool ERP

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

### 1.3. Матрица доступа

| Источник → Цель | Ядро | Домен А | Домен Б |
|-----------------|:----:|:-------:|:-------:|
| **Ядро** | ✅ | ❌ | ❌ |
| **Домен А** | ✅ (F-Keys, JOINs) | ✅ (внутри) | ❌ (только реплика) |
| **Домен Б** | ✅ (F-Keys, JOINs) | ❌ (только реплика) | ✅ (внутри) |

### 1.4. Первый домен: Operations

| Сущность | Назначение |
|----------|-----------|
| `oper_goods` | Товары |
| `oper_legal_entities` | Юридические лица |
| `oper_locations` | Локации / места |
| `oper_persons` | Физические лица |
| `oper_regions` | Регионы |
| `oper_vat_invoices` | Счета-фактуры НДС |
| `oper_warehouses` | Склады |
| `oper_bank_accounts` | Банковские счета |

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
│ 11. Применение изменения к реплике                              │
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
-- Записывается в той же транзакции, что и основное изменение.
-- Одно событие может порождать несколько задач (по одной на домен).

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
-- Монотонно растущий номер внутри каждой группы.
-- Атомарно увеличивается через INSERT ... ON CONFLICT ... RETURNING.

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
-- Уникальность по (event_id, consumer_domain) гарантирует,
-- что одно событие применяется каждым доменом ровно один раз.

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
-- Одна запись в core_outbox порождает несколько задач
-- (по одной на каждый подписанный домен).

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
-- «Курсор» каждой группы: последний успешно применённый sequence_no.
-- Задача может применяться только при sequence_no = last_applied + 1.

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
CREATE TABLE public.sales_oper_goods_replica (
    -- ID оригинала из oper_goods (БЕЗ ForeignKey на чужой домен!)
    goods_id          UUID PRIMARY KEY,

    -- Скопированные данные
    name              VARCHAR(255) NOT NULL,
    code              VARCHAR(64),
    tenant_id         UUID         NOT NULL,

    -- Метаданные синхронизации
    replica_version   INTEGER      NOT NULL DEFAULT 1,
    replica_synced_at TIMESTAMPTZ  NOT NULL DEFAULT now(),
    is_deleted        BOOLEAN      NOT NULL DEFAULT false
);

CREATE INDEX idx_sales_oper_goods_replica_tenant
    ON public.sales_oper_goods_replica (tenant_id);

COMMENT ON TABLE public.sales_oper_goods_replica IS
    'Реплика товаров из домена operations.';
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
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, unique=False
    )
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
            # Выборка задач, готовых к применению:
            # sequence_no = last_applied_sequence + 1
            stmt = text("""
                SELECT t.*
                FROM core_replication_tasks t
                LEFT JOIN core_replication_progress p
                    ON  p.consumer_domain = t.target_domain
                    AND p.ordering_key    = t.ordering_key
                WHERE t.status IN ('pending', 'waiting')
                  AND (t.next_retry_at IS NULL OR t.next_retry_at <= now())
                  AND (
                      -- Нет записи в progress и это первая задача (sequence_no = 1 или 0)
                      (p.last_applied_sequence IS NULL AND t.sequence_no <= 1)
                      OR
                      -- Есть запись и это следующая задача
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
                # Обновляем статус "ожидающих" задач (у которых предыдущая ещё не применена)
                await self._mark_waiting_tasks(db)
                return

            for row in rows:
                task_id = row.id
                await self._apply_task_by_id(db, task_id)

            await db.commit()

    async def _mark_waiting_tasks(self, db: AsyncSession) -> None:
        """Пометить задачи как waiting, если их предыдущая ещё не применена."""
        # Упрощённо: помечаем waiting те pending задачи, у которых
        # sequence_no > last_applied + 1 и они старше 10 секунд
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
        # Загружаем задачу
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
            # Пропуск в последовательности состояний — ждём
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
# import app.sales.replica.handlers     # noqa: F401
# import app.hr.replica.handlers        # noqa: F401


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
                "id": str(new_goods.id),
                "name": new_goods.name,
                "code": new_goods.code,
                "tenant_id": str(new_goods.tenant_id),
                "is_deleted": False,
            },
            ordering_key=f"operations:oper_goods:{new_goods.id}",
        )
        # Commit в роутере
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

        if current == new_status:
            return  # Идемпотентность

        if new_status not in ORDER_TRANSITIONS.get(current, set()):
            # Пропуск промежуточного состояния → ждём
            raise SequenceGapError(
                f"Недопустимый переход {current} → {new_status}"
            )

        replica.status = new_status
        replica.replica_version += 1
```

### 7.4. Обработчик реплики товаров

```python
# backend/app/sales/replica/handlers.py
from app.core.events.handlers import register_handler

class OperGoodsReplicaHandler:
    def get_target_table(self) -> str:
        return "sales_oper_goods_replica"

    def get_target_domain(self) -> str:
        return "sales"

    async def apply(self, db, payload, operation):
        goods_id = payload["id"]

        if operation == "delete":
            stmt = select(SalesOperGoodsReplicaModel).where(
                SalesOperGoodsReplicaModel.goods_id == goods_id
            )
            replica = (await db.execute(stmt)).scalar_one_or_none()
            if replica:
                replica.is_deleted = True
                replica.replica_version += 1
                replica.replica_synced_at = datetime.now(timezone.utc)
            return

        stmt = select(SalesOperGoodsReplicaModel).where(
            SalesOperGoodsReplicaModel.goods_id == goods_id
        )
        replica = (await db.execute(stmt)).scalar_one_or_none()

        if replica is None:
            replica = SalesOperGoodsReplicaModel(
                goods_id=goods_id,
                name=payload["name"],
                code=payload.get("code"),
                tenant_id=payload["tenant_id"],
            )
            db.add(replica)
        else:
            replica.name = payload["name"]
            replica.code = payload.get("code")
            replica.is_deleted = payload.get("is_deleted", False)
            replica.replica_version += 1
            replica.replica_synced_at = datetime.now(timezone.utc)


# Регистрация при импорте
register_handler(
    target_domain="sales",
    aggregate_type="oper_goods",
    handler=OperGoodsReplicaHandler(),
)
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
| Backend №1 | `@property` для `is_editing_locked`, `lazy="selectin"` |
| Backend №26 | Мульти-арендность через фильтрацию `tenant_id` |
| Backend №28 | `{"schema": "public"}`, именованные ограничения |
| Backend №31 | `flush` в CRUD, `commit` в роутере |
| Backend №40 | Двойные блокировки (оптимистическая + пессимистическая) |
| ТЗ §3.3 | Контракт атрибутов доступа через `DocumentAccessMixin` |

---

# Интервал опроса и возможность подписки на события

## 1. Где определяется интервал опроса

В текущей архитектуре интервал опроса задаётся в классе `Replicator` (`backend/app/core/events/replicator.py`) как константа класса:

```python
class Replicator:
    """Фоновый процесс репликации."""

    POLL_INTERVAL: float = 2.0      # ← Интервал опроса (секунды)
    BATCH_SIZE: int = 50            # Размер батча событий/задач
    MAX_ATTEMPTS: int = 5           # Максимум попыток обработки задачи
    MAX_RETRY_DELAY: int = 60       # Максимальная задержка повторной попытки

    async def run(self) -> None:
        """Главный цикл репликатора."""
        logger.info("[Replicator] Запуск фонового процесса репликации")
        while True:
            try:
                await self._process_outbox()   # Чтение событий
                await self._process_tasks()    # Применение задач
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.exception("[Replicator] Ошибка цикла: %s", str(e))
            await asyncio.sleep(self.POLL_INTERVAL)   # ← Пауза между опросами
```

### Иерархия параметров тюнинга

| Параметр | Где задан | Назначение | Типичные значения |
|----------|-----------|-----------|-------------------|
| `POLL_INTERVAL` | `Replicator.POLL_INTERVAL` | Пауза между циклами опроса | 0.5–5 секунд |
| `BATCH_SIZE` | `Replicator.BATCH_SIZE` | Сколько событий за один цикл | 10–100 |
| `MAX_ATTEMPTS` | `Replicator.MAX_ATTEMPTS` | Попыток до статуса `failed` | 3–10 |
| `MAX_RETRY_DELAY` | `Replicator.MAX_RETRY_DELAY` | Максимум экспоненциальной задержки | 30–120 секунд |

**Возможности конфигурирования:**

```python
# Вариант 1: Переопределение через переменные окружения
import os

class Replicator:
    POLL_INTERVAL: float = float(os.getenv("REPLICATOR_POLL_INTERVAL", "2.0"))
    BATCH_SIZE: int = int(os.getenv("REPLICATOR_BATCH_SIZE", "50"))

# Вариант 2: Параметры из таблицы настроек
# Вариант 3: Несколько репликаторов с разными интервалами
#           (например, для склада 0.5 сек, для остальных 5 сек)
```

---

## 2. Есть ли возможность подписки на события

В текущей архитектуре — **только поллинг** (активный опрос таблицы `core_outbox`). Однако можно добавить **подписку** через механизм **PostgreSQL `LISTEN/NOTIFY`**. Разберу три варианта.

### Вариант A: Поллинг (текущая архитектура)

```
┌─────────────────────────────────────────────┐
│  МАСТЕР-ДОМЕН                               │
│  Транзакция:                                │
│    1. Изменение данных                      │
│    2. Запись в core_outbox                  │
│    3. COMMIT                                │
└──────────────────┬──────────────────────────┘
                   │ (событие лежит в таблице)
                   ▼
┌─────────────────────────────────────────────┐
│  РЕПЛИКАТОР                                 │
│  Каждые 2 секунды:                          │
│    SELECT * FROM core_outbox                │
│    WHERE processed = false                  │
└─────────────────────────────────────────────┘
```

**Характеристики:**
- Задержка репликации: **до `POLL_INTERVAL` секунд** (в среднем половина)
- Гарантированная доставка: ✅ да (событие лежит в таблице, пока не обработано)
- Сложность: минимальная
- Нагрузка: постоянный опрос даже при отсутствии событий

### Вариант B: Подписка через `LISTEN/NOTIFY`

PostgreSQL имеет встроенный механизм асинхронных уведомлений. Его можно использовать для мгновенного оповещения репликатора о новых событиях.

**Шаг 1. Публикация уведомления при записи события**

```python
# backend/app/core/events/outbox.py
class OutboxPublisher:
    async def publish(self, db, *, event_type, source_domain, ...) -> None:
        # 1. Запись в core_outbox (как сейчас)
        stmt = insert(CoreOutboxModel).values(...)
        await db.execute(stmt)

        # 2. НОВОЕ: уведомление после коммита транзакции
        #    (выполняется в той же транзакции, но срабатывает при COMMIT)
        await db.execute(
            text("SELECT pg_notify('core_outbox_notify', :event_id::text)"),
            {"event_id": event_id},
        )
```

**Шаг 2. Подписка репликатора**

```python
# backend/app/core/events/replicator.py
import asyncpg

class Replicator:
    NOTIFY_CHANNEL: str = "core_outbox_notify"

    async def run(self) -> None:
        # Отдельное подключение для подписки
        # (нельзя использовать пул сессий — подписка занимает соединение)
        conn = await asyncpg.connect(dsn=DATABASE_URL)

        async def on_notification(conn, pid, channel, payload):
            logger.info("[Replicator] Получено уведомление: %s", payload)
            await self._process_outbox()  # Немедленная обработка
            await self._process_tasks()

        await conn.add_listener(self.NOTIFY_CHANNEL, on_notification)

        try:
            # Основной цикл остаётся как страховка
            while True:
                await asyncio.sleep(self.POLL_INTERVAL)
                await self._process_outbox()
                await self._process_tasks()
        finally:
            await conn.close()
```

**Характеристики:**
- Задержка репликации: **~10–50 мс** (мгновенно после коммита)
- Гарантированная доставка: ⚠️ **нет** — если репликатор не подключён в момент уведомления, событие пройдёт мимо канала
- Сложность: средняя (отдельное подключение, обработка переподключений)
- Нагрузка: минимальная (нет постоянного опроса)

### Вариант C: Гибридный подход (рекомендуемый)

**Подписка для снижения задержки + поллинг как страховка.**

```
┌───────────────────────────────────────────────────────────┐
│  МАСТЕР-ДОМЕН                                             │
│  Транзакция:                                              │
│    1. Изменение данных                                    │
│    2. Запись в core_outbox                                │
│    3. pg_notify('core_outbox_notify')                     │
│    4. COMMIT                                              │
└──────────────┬────────────────────────────────────────────┘
               │
               ├──── NOTIFY (мгновенно) ────► Репликатор обрабатывает сразу
               │
               └──── Если уведомление потеряно ────►
                    Поллинг каждые 30 секунд подхватит событие
```

```python
class Replicator:
    POLL_INTERVAL_FAST: float = 0.1     # При активной подписке
    POLL_INTERVAL_FALLBACK: float = 30  # Страховочный опрос

    async def run(self) -> None:
        conn = await asyncpg.connect(dsn=DATABASE_URL)
        await conn.add_listener(
            self.NOTIFY_CHANNEL,
            self._on_notification,
        )
        while True:
            # Страховочный цикл: даже если все уведомления потеряны,
            # раз в 30 секунд проверим таблицу
            await asyncio.sleep(self.POLL_INTERVAL_FALLBACK)
            await self._process_outbox()
            await self._process_tasks()
```

**Характеристики:**
- Задержка репликации: ~10–50 мс в нормальном режиме
- Гарантированная доставка: ✅ да (страховочный поллинг)
- Сложность: высокая (два механизма)
- Нагрузка: минимальная

---

## 3. Сравнение вариантов

| Аспект | Поллинг (текущий) | Подписка | Гибрид |
|--------|:---:|:---:|:---:|
| Задержка репликации | до `POLL_INTERVAL` | ~10–50 мс | ~10–50 мс |
| Гарантированная доставка | ✅ | ❌ | ✅ |
| Работа после перезапуска | ✅ | ⚠️ Требует переподключения | ✅ |
| Нагрузка на БД | Постоянный опрос | Минимальная | Минимальная |
| Сложность реализации | Низкая | Средняя | Высокая |
| Отказоустойчивость | Высокая | Средняя | Высокая |

---

## 4. Почему текущая архитектура выбрала поллинг

| Причина | Пояснение |
|---------|-----------|
| **Гарантия доставки** | Событие лежит в таблице `core_outbox`, пока не обработано. Даже при падении репликатора после перезапуска все необработанные события будут подхвачены. |
| **Идемпотентность** | Поллинг естественно сочетается с `core_inbox` и проверкой `sequence_no = last_applied + 1`. |
| **Простота** | Нет отдельного подключения для подписки, нет обработки переподключений, нет потери уведомлений. |
| **Достаточность для монолита** | В модульном монолите задержка 1–2 секунды обычно приемлема. Для склада с критичным порядком важен порядок, а не скорость. |

---

## 5. Когда стоит переходить на подписку

| Сценарий | Рекомендация |
|----------|--------------|
| Задержка 1–2 секунды приемлема | Оставить поллинг |
| Нужна задержка < 100 мс | Гибридный подход (вариант C) |
| Распределение доменов на разные серверы | Обязательна подписка или брокер сообщений (RabbitMQ, Kafka) |
| Высокая нагрузка на БД от опроса | Подписка + редкий страховочный поллинг |

---

## 6. Итоговый ответ на вопрос

| Вопрос | Ответ |
|--------|-------|
| **Где определяется интервал опроса?** | В классе `Replicator` (`backend/app/core/events/replicator.py`), константа `POLL_INTERVAL: float = 2.0`, используется в `await asyncio.sleep(self.POLL_INTERVAL)` внутри цикла `run()` |
| **Есть ли возможность подписки?** | В текущей архитектуре — нет, только поллинг. Технически возможна через `LISTEN/NOTIFY` PostgreSQL (варианты B и C выше). Рекомендуемый путь — **гибрид**: подписка для снижения задержки + поллинг как страховка от потерянных уведомлений |

Если нужно реализовать подписку для конкретного домена (например, `operations` для складских движений) — сообщите, подготовлю точечные изменения в `outbox.py` и `replicator.py` без изменения остальной архитектуры.

---
**Конец документа.** Данный документ является единственным источником истины по архитектуре модульного монолита и механизму репликации между доменами. Любое отклонение подлежит исправлению при код-ревью.