-- ═══════════════════════════════════════════════════════════════
-- МОДУЛЬ: Заказы продаж (пилот сложной формы)
-- Таблицы: sales_orders, sales_order_lines
-- ═══════════════════════════════════════════════════════════════

-- ============================================================
-- 1. ОСНОВНАЯ ТАБЛИЦА ЗАКАЗОВ
-- ============================================================
CREATE TABLE public.sales_orders (
    id                     UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Контракт доступа (§3.3)
    tenant_id              UUID NOT NULL REFERENCES public.tenants(id),
    section_id             UUID NOT NULL REFERENCES public.sections(id),
    author_id              UUID NOT NULL REFERENCES public.users(id),
    or_tags                VARCHAR(128)[],
    and_tags               VARCHAR(128)[],

    -- Жизненный цикл
    doc_status             VARCHAR(32)  NOT NULL DEFAULT 'draft',
    doc_number             VARCHAR(64),
    doc_date               DATE,
    version                INTEGER      NOT NULL DEFAULT 1,
    editing_by_user_id     UUID REFERENCES public.users(id),
    editing_since          TIMESTAMPTZ,
    created_at             TIMESTAMPTZ  NOT NULL DEFAULT now(),
    created_by_user_id     UUID REFERENCES public.users(id),
    updated_at             TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_by_user_id     UUID REFERENCES public.users(id),
    deleted_at             TIMESTAMPTZ,
    deleted_by_user_id     UUID REFERENCES public.users(id),

    -- Бизнес-поля заказа
    supplier_id            UUID NOT NULL REFERENCES public.bp_companies(id),
    customer_id            UUID NOT NULL REFERENCES public.bp_companies(id),
    contact                VARCHAR(255) NOT NULL,
    manager_id             UUID NOT NULL REFERENCES public.users(id),
    delivery_due_date      DATE NOT NULL,
    payment_scheme         VARCHAR(512),
    currency_id            UUID NOT NULL REFERENCES public.currencies(id),
    total_amount           NUMERIC(18,2) NOT NULL DEFAULT 0,
    delivery_address       TEXT,
    delivery_method        VARCHAR(32)
        CONSTRAINT chk_sales_orders_delivery_method
        CHECK (delivery_method IN ('pickup', 'own_transport', 'third_party') OR delivery_method IS NULL)
);

-- Индексы
CREATE INDEX idx_sales_orders_tenant_id       ON public.sales_orders (tenant_id);
CREATE INDEX idx_sales_orders_section_id      ON public.sales_orders (section_id);
CREATE INDEX idx_sales_orders_supplier_id     ON public.sales_orders (supplier_id);
CREATE INDEX idx_sales_orders_customer_id     ON public.sales_orders (customer_id);
CREATE INDEX idx_sales_orders_manager_id      ON public.sales_orders (manager_id);
CREATE INDEX idx_sales_orders_tenant_status   ON public.sales_orders (tenant_id, doc_status);
CREATE INDEX idx_sales_orders_editing_by      ON public.sales_orders (editing_by_user_id);
CREATE INDEX idx_sales_orders_or_tags         ON public.sales_orders USING GIN (or_tags);
CREATE INDEX idx_sales_orders_and_tags        ON public.sales_orders USING GIN (and_tags);

-- Частичный индекс для активных заказов
CREATE INDEX idx_sales_orders_active          ON public.sales_orders (tenant_id)
    WHERE deleted_at IS NULL;

COMMENT ON TABLE public.sales_orders IS
    'Заказы продаж — документный модуль (пилот сложной формы). '
    'Наследует контракт доступа (§3.3) и жизненный цикл документа.';


-- ============================================================
-- 2. ТАБЛИЦА СТРОК СПЕЦИФИКАЦИИ
-- ============================================================
CREATE TABLE public.sales_order_lines (
    id                     UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id               UUID NOT NULL
        REFERENCES public.sales_orders(id) ON DELETE CASCADE,
    line_no                INTEGER      NOT NULL,
    goods_id               UUID         NOT NULL,  -- FK на реплику товаров добавляется позже
    quantity               NUMERIC(18,4) NOT NULL,
    price_with_vat         NUMERIC(18,2) NOT NULL,
    discount_percent       NUMERIC(5,2)  NOT NULL DEFAULT 0,
    vat_rate_percent       NUMERIC(5,2)  NOT NULL DEFAULT 0,
    created_at             TIMESTAMPTZ   NOT NULL DEFAULT now(),
    updated_at             TIMESTAMPTZ   NOT NULL DEFAULT now(),

    CONSTRAINT uq_sales_order_line_order_line_no
        UNIQUE (order_id, line_no),
    CONSTRAINT chk_sales_order_line_quantity
        CHECK (quantity >= 0),
    CONSTRAINT chk_sales_order_line_price
        CHECK (price_with_vat >= 0),
    CONSTRAINT chk_sales_order_line_discount
        CHECK (discount_percent >= 0 AND discount_percent <= 100),
    CONSTRAINT chk_sales_order_line_vat_rate
        CHECK (vat_rate_percent >= 0 AND vat_rate_percent <= 100)
);

-- Индексы
CREATE INDEX idx_sales_order_lines_order_id   ON public.sales_order_lines (order_id);
CREATE INDEX idx_sales_order_lines_goods_id   ON public.sales_order_lines (goods_id);

COMMENT ON TABLE public.sales_order_lines IS
    'Строки спецификации заказа продаж. '
    'Вычисляемые поля (line_total, amount_with_discount, vat_amount) '
    'реализованы через @property модели, не хранятся в БД.';