-- ═══════════════════════════════════════════════════
-- ДОМЕН: BUSINESS_PARTNERS (префикс bp_)
-- Сущность: Компании (юрлица)
-- Наследует: DocumentAccessMixin + DocumentLifecycleMixin
-- ═══════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS public.bp_companies
(
    id                     uuid NOT NULL DEFAULT uuid_generate_v4(),

    -- Специфичные поля сущности
    name                   text NOT NULL,
    fullname               text,
    inn                    text,
    address_legal          text,
    address_fact           text,
    phone                  text,
    email                  text,
    contact                text,
    is_customer            boolean,
    is_supplier            boolean,
    kpp                    text,
    region_id              uuid,

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

    -- Первичный ключ (исправлено имя ограничения)
    CONSTRAINT bp_companies_pkey PRIMARY KEY (id)
);

-- Индексы для мультитенантности и производительности
CREATE INDEX idx_bp_companies_tenant_id    ON public.bp_companies (tenant_id);
CREATE INDEX idx_bp_companies_section_id   ON public.bp_companies (section_id);
CREATE INDEX idx_bp_companies_author_id    ON public.bp_companies (author_id);
CREATE INDEX idx_bp_companies_region_id    ON public.bp_companies (region_id);
CREATE INDEX idx_bp_companies_inn          ON public.bp_companies (tenant_id, inn);
CREATE INDEX idx_bp_companies_name         ON public.bp_companies (tenant_id, name);
CREATE INDEX idx_bp_companies_or_tags      ON public.bp_companies USING GIN (or_tags);
CREATE INDEX idx_bp_companies_and_tags     ON public.bp_companies USING GIN (and_tags);
CREATE INDEX idx_bp_companies_editing_by   ON public.bp_companies (editing_by_user_id);
CREATE INDEX idx_bp_companies_tenant_status ON public.bp_companies (tenant_id, doc_status);

-- Частичный индекс для активных документов (мягкое удаление)
CREATE INDEX idx_bp_companies_active       ON public.bp_companies (tenant_id) WHERE deleted_at IS NULL;

-- Уникальность ИНН в рамках организации (опционально, раскомментируйте при необходимости)
-- CREATE UNIQUE INDEX uq_bp_companies_tenant_inn
--     ON public.bp_companies (tenant_id, inn)
--     WHERE inn IS NOT NULL AND deleted_at IS NULL;

COMMENT ON TABLE public.bp_companies
    IS 'Компании (юрлица) — домен business_partners';