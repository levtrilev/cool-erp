-- ═══════════════════════════════════════════════════
-- ДОМЕН: BUSINESS_PARTNERS
-- Реплика регионов из домена SALES
-- ✅ ПОЛНЫЙ КОНТРАКТ ДОСТУПА (раздел 4.10 ТЗ)
-- ═══════════════════════════════════════════════════

-- Если таблица уже создана — сначала удалить (или использовать миграцию)
-- DROP TABLE IF EXISTS public.bp_sales_regions_replica;

CREATE TABLE IF NOT EXISTS public.bp_sales_regions_replica (
    -- ID оригинала из домена sales (БЕЗ ForeignKey на чужой домен!)
    region_id         UUID PRIMARY KEY,

    -- Скопированные бизнес-данные
    name              VARCHAR(128) NOT NULL,
    capital           VARCHAR(128),
    code              VARCHAR(8),
    area              VARCHAR(64),

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
CREATE INDEX idx_bp_sales_regions_replica_tenant
    ON public.bp_sales_regions_replica (tenant_id);
CREATE INDEX idx_bp_sales_regions_replica_section
    ON public.bp_sales_regions_replica (section_id);
CREATE INDEX idx_bp_sales_regions_replica_or_tags
    ON public.bp_sales_regions_replica USING GIN (or_tags);
CREATE INDEX idx_bp_sales_regions_replica_and_tags
    ON public.bp_sales_regions_replica USING GIN (and_tags);
CREATE INDEX idx_bp_sales_regions_replica_active
    ON public.bp_sales_regions_replica (tenant_id)
    WHERE is_deleted = false;

COMMENT ON TABLE public.bp_sales_regions_replica IS
    'Реплика регионов из домена sales. '
    'Содержит полный контракт доступа (§3.3) для вычисления '
    'видимости и уровня через AccessService.';