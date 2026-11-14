-- Миграция: связь товара с типом номенклатуры + копия единицы измерения
ALTER TABLE public.sales_goods
    ADD COLUMN IF NOT EXISTS item_type_id UUID NULL;

ALTER TABLE public.sales_goods
    ADD CONSTRAINT fk_sales_goods_item_type
    FOREIGN KEY (item_type_id) REFERENCES public.sales_item_types (id);

CREATE INDEX IF NOT EXISTS idx_sales_goods_item_type
    ON public.sales_goods (item_type_id);

ALTER TABLE public.sales_goods
    ADD COLUMN IF NOT EXISTS base_uom VARCHAR(64) NULL;

COMMENT ON COLUMN public.sales_goods.item_type_id IS
    'Тип номенклатуры (справочник sales_item_types), NULL допустим';
COMMENT ON COLUMN public.sales_goods.base_uom IS
    'Единица измерения основная: копия из типа номенклатуры на момент выбора';