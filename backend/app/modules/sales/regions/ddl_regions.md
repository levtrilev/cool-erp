-- ═══════════════════════════════════════════════════
-- ДОМЕН: SALES (префикс sales_)
-- Сущность: Регионы
-- Наследует: DocumentAccessMixin + DocumentLifecycleMixin
-- ═══════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS public.sales_regions
(
    id                     uuid NOT NULL DEFAULT uuid_generate_v4(),

    -- Специфичные поля сущности
    name                   character varying(128) NOT NULL,
    capital                character varying(128),
    code                   character varying(8),
    area                   character varying(64),

    -- Контракт доступа (ТЗ §3.3, DocumentAccessMixin)
    tenant_id              uuid NOT NULL REFERENCES public.tenants(id),
    section_id             uuid NOT NULL REFERENCES public.sections(id),
    author_id              uuid NOT NULL REFERENCES public.users(id),
    or_tags                varchar(128)[],
    and_tags               varchar(128)[],

    -- Жизненный цикл (DocumentLifecycleMixin)
    doc_status             varchar(32) NOT NULL DEFAULT 'draft',
    doc_number             varchar(64),
    doc_date               date,
    version                integer NOT NULL DEFAULT 1,
    editing_by_user_id     uuid REFERENCES public.users(id),
    editing_since          timestamptz,
    created_at             timestamptz NOT NULL DEFAULT now(),
    created_by_user_id     uuid REFERENCES public.users(id),
    updated_at             timestamptz NOT NULL DEFAULT now(),
    updated_by_user_id     uuid REFERENCES public.users(id),
    deleted_at             timestamptz,
    deleted_by_user_id     uuid REFERENCES public.users(id),

    CONSTRAINT sales_regions_pkey PRIMARY KEY (id)
);

-- Индексы для мультитенантности и производительности
CREATE INDEX idx_sales_regions_tenant_id    ON public.sales_regions (tenant_id);
CREATE INDEX idx_sales_regions_section_id   ON public.sales_regions (section_id);
CREATE INDEX idx_sales_regions_author_id    ON public.sales_regions (author_id);
CREATE INDEX idx_sales_regions_code         ON public.sales_regions (tenant_id, code);
CREATE INDEX idx_sales_regions_name         ON public.sales_regions (tenant_id, name);
CREATE INDEX idx_sales_regions_or_tags      ON public.sales_regions USING GIN (or_tags);
CREATE INDEX idx_sales_regions_and_tags     ON public.sales_regions USING GIN (and_tags);
CREATE INDEX idx_sales_regions_editing_by   ON public.sales_regions (editing_by_user_id);
CREATE INDEX idx_sales_regions_tenant_status ON public.sales_regions (tenant_id, doc_status);

-- Частичный индекс для активных документов (мягкое удаление)
CREATE INDEX idx_sales_regions_active       ON public.sales_regions (tenant_id) WHERE deleted_at IS NULL;

COMMENT ON TABLE public.sales_regions
    IS 'Регионы — домен sales';