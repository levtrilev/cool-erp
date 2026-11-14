-- backend/alembic или ручной DDL: sales_item_types
CREATE TABLE public.sales_item_types (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name                 VARCHAR(255) NOT NULL,
    description          TEXT,
    item_class           VARCHAR(32) NOT NULL,
    serial_tracking      BOOLEAN NOT NULL DEFAULT false,
    expiration_tracking  BOOLEAN NOT NULL DEFAULT false,
    vat_rate             NUMERIC(5,2) NOT NULL DEFAULT 0,
    base_uom             VARCHAR(64),
    price_group          VARCHAR(128),
    supply_type          VARCHAR(128),
    has_variants         BOOLEAN NOT NULL DEFAULT false,
    -- Контракт доступа (§3.3)
    tenant_id            UUID NOT NULL REFERENCES public.tenants(id),
    section_id           UUID NOT NULL REFERENCES public.sections(id),
    author_id            UUID NOT NULL REFERENCES public.users(id),
    or_tags              VARCHAR(128)[],
    and_tags             VARCHAR(128)[],
    -- Жизненный цикл
    doc_status           VARCHAR(32) NOT NULL DEFAULT 'draft',
    doc_number           VARCHAR(64),
    doc_date             DATE,
    version              INTEGER NOT NULL DEFAULT 1,
    editing_by_user_id   UUID REFERENCES public.users(id),
    editing_since        TIMESTAMPTZ,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by_user_id   UUID REFERENCES public.users(id),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by_user_id   UUID REFERENCES public.users(id),
    deleted_at           TIMESTAMPTZ,
    deleted_by_user_id   UUID REFERENCES public.users(id),
    CONSTRAINT chk_sales_item_types_class
        CHECK (item_class IN ('GOODS','SERVICE','LABOR','SEMI_FINISHED',
                              'RAW_MATERIAL','BUNDLE','PACKAGING'))
);

CREATE INDEX idx_sales_item_types_tenant   ON public.sales_item_types (tenant_id);
CREATE INDEX idx_sales_item_types_section  ON public.sales_item_types (section_id);
CREATE INDEX idx_sales_item_types_or_tags  ON public.sales_item_types USING GIN (or_tags);
CREATE INDEX idx_sales_item_types_and_tags ON public.sales_item_types USING GIN (and_tags);
CREATE INDEX idx_sales_item_types_editing  ON public.sales_item_types (editing_by_user_id);
CREATE INDEX idx_sales_item_types_active   ON public.sales_item_types (tenant_id)
    WHERE deleted_at IS NULL;

COMMENT ON TABLE public.sales_item_types IS
    'Типы номенклатуры (ItemTypes) домена sales: документный модуль с контрактом доступа и жизненным циклом.';

-- Регистрация типа документа в реестре (идемпотентно)
-- INSERT INTO public.doctypes (doctype, doctype_name, domain, is_active, apply_or_tags, apply_and_tags)
-- VALUES ('sales_item_types', 'Типы номенклатуры', 'sales', true, false, false)
-- ON CONFLICT (doctype) DO NOTHING;