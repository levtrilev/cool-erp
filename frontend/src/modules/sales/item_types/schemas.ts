// frontend/src/modules/sales/item_types/schemas.ts
import { z } from "zod";

/** ✅ Правило №41: Zod-схема формы типа номенклатуры. */
export const itemTypeFormSchema = z.object({
  name: z.string().min(1, "Наименование обязательно").max(255),
  description: z.string().max(4096).optional(),
  item_class: z.string().min(1, "Выберите класс номенклатуры"),
  serial_tracking: z.boolean().optional(),
  expiration_tracking: z.boolean().optional(),
  vat_rate: z.coerce.number().min(0, "Не меньше 0").max(100, "Не больше 100"),
  base_uom: z.string().max(64).optional(),
  price_group: z.string().max(128).optional(),
  supply_type: z.string().max(128).optional(),
  has_variants: z.boolean().optional(),
  // Контракт документа
  section_id: z.string().min(1, "Выберите раздел"),
  doc_status: z.string().min(1, "Выберите статус"),
  doc_number: z.string().max(64).optional(),
  doc_date: z.string().optional(),
  or_tags: z.array(z.string()).optional(),
  and_tags: z.array(z.string()).optional(),
  version: z.number().int().positive().optional(),
});

export type ItemTypeFormData = z.infer<typeof itemTypeFormSchema>;

/** ✅ Правило №20: константа сброса вне компонента. */
export const CREATE_DEFAULTS: ItemTypeFormData = {
  name: "",
  description: "",
  item_class: "GOODS",
  serial_tracking: false,
  expiration_tracking: false,
  vat_rate: 0,
  base_uom: "",
  price_group: "",
  supply_type: "",
  has_variants: false,
  section_id: "",
  doc_status: "draft",
  doc_number: "",
  doc_date: "",
  or_tags: [],
  and_tags: [],
  version: undefined,
};

/**
 * Значения enum хранятся в БД, пользователю показываются подписи.
 * Единственный источник соответствий для формы и списка.
 */
export const ITEM_CLASS_LABELS: Record<string, string> = {
  GOODS: "Товар",
  SERVICE: "Услуга",
  LABOR: "Работа",
  SEMI_FINISHED: "Полуфабрикат",
  RAW_MATERIAL: "Материал",
  BUNDLE: "Набор",
  PACKAGING: "Тара",
};
