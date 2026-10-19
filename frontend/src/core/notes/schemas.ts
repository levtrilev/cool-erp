import { z } from "zod";

/**
 * Zod-схема валидации формы заметки.
 * Формат тега (ТЗ §6.2): <пространство>:<значение>, без пробелов.
 */
export const tagPattern = /^[^\s:]+:[^\s:]+$/;

export const noteFormSchema = z.object({
  title: z
    .string()
    .min(1, "Название обязательно")
    .max(255, "Максимум 255 символов"),
  content: z.string().optional(),
  section_id: z.string().min(1, "Раздел обязателен"),
  doc_status: z.enum([
    "draft",
    "pending",
    "approved",
    "active",
    "archived",
  ]),
  doc_number: z.string().max(64).optional(),
  doc_date: z.string().optional(),
  or_tags: z
    .array(
      z.string().regex(tagPattern, "Формат тега: пространство:значение")
    )
    .optional(),
  and_tags: z
    .array(
      z.string().regex(tagPattern, "Формат тега: пространство:значение")
    )
    .optional(),
  version: z.number().int().min(1).optional(),
});

export type NoteFormData = z.infer<typeof noteFormSchema>;

export const CREATE_DEFAULTS: NoteFormData = {
  title: "",
  content: "",
  section_id: "",
  doc_status: "draft",
  doc_number: "",
  doc_date: "",
  or_tags: [],
  and_tags: [],
  version: undefined,
};

export const DOC_STATUS_LABELS: Record<string, string> = {
  draft: "Черновик",
  pending: "На утверждении",
  approved: "Утверждён",
  active: "Действует",
  archived: "Архив",
};