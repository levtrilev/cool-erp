-- ════════════════════════════════════════════════════════════
-- МОДУЛЬ: Справочник валют (ядро, core)
-- Таблица: currencies
-- Глобальный справочник (без tenant_id), доступен всем доменам.
-- Соответствует ISO 4217.
-- ════════════════════════════════════════════════════════════

CREATE TABLE public.currencies (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code            VARCHAR(3)   NOT NULL,
    name            VARCHAR(255) NOT NULL,
    symbol          VARCHAR(10),
    numeric_code    INTEGER,
    is_active       BOOLEAN      NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),

    CONSTRAINT uq_currencies_code UNIQUE (code)
);

-- Индексы
CREATE INDEX idx_currencies_code      ON public.currencies (code);
CREATE INDEX idx_currencies_is_active ON public.currencies (is_active);

COMMENT ON TABLE public.currencies IS
    'Справочник валют (ISO 4217). Глобальный, доступен всем доменам. '
    'Ссылка из документов через currency_id.';

<!-- Начальные данные (seed) -->
INSERT INTO public.currencies (code, name, symbol, numeric_code, is_active) VALUES
    ('RUB', 'Российский рубль', '₽', 643, true),
    ('USD', 'Доллар США',       '$', 840, true),
    ('EUR', 'Евро',             '€', 978, true),
    ('BYN', 'Белорусский рубль','Br',933, true),
    ('KZT', 'Казахстанский тенге','₸',398, true),
    ('CNY', 'Китайский юань',   '¥', 156, true)
ON CONFLICT ON CONSTRAINT uq_currencies_code DO NOTHING;