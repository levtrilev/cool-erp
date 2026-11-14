// frontend/src/modules/sales/goods/schemas.ts (новый файл)
import { z } from "zod";

/** ✅ Правило №41: Zod-схема формы товара. */
export const goodFormSchema = z.object({
  name: z.string().min(1, "Название обязательно").max(255),
  description: z.string().max(4096).optional(),
  item_type_id: z.string().optional(),
  base_uom: z.string().max(64).optional(),
  // Контракт документа
  section_id: z.string().min(1, "Выберите раздел"),
  doc_status: z.string().min(1, "Выберите статус"),
  doc_number: z.string().max(64).optional(),
  doc_date: z.string().optional(),
  or_tags: z.array(z.string()).optional(),
  and_tags: z.array(z.string()).optional(),
  version: z.number().int().positive().optional(),
});

export type GoodFormData = z.infer<typeof goodFormSchema>;

/** ✅ Правило №20: константа сброса вне компонента. */
export const CREATE_DEFAULTS: GoodFormData = {
  name: "",
  description: "",
  item_type_id: "",
  base_uom: "",
  section_id: "",
  doc_status: "draft",
  doc_number: "",
  doc_date: "",
  or_tags: [],
  and_tags: [],
  version: undefined,
};