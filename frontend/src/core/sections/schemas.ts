import { z } from "zod";

// ✅ Правило №41: схема валидации через z.object
export const sectionFormSchema = z.object({
  name: z
    .string()
    .min(1, "Название обязательно")
    .max(255, "Максимум 255 символов"),
  description: z.string().optional(),
  // ✅ tenant_id — только для отображения в режиме редактирования,
  // не отправляется в мутациях (тенант раздела изменить нельзя)
  tenant_id: z.string().optional(),
});

export type SectionFormData = z.infer<typeof sectionFormSchema>;

// ✅ Правило №20: константа вне компонента
export const CREATE_DEFAULTS: SectionFormData = {
  name: "",
  description: "",
  tenant_id: "",
};

// ✅ Человекочитаемые имена типов разделов (ТЗ §4.1)
export const SECTION_TYPE_LABELS: Record<string, string> = {
  platform: "Общий (платформенный)",
  tenant_default: "Общий для организации",
  custom: "Произвольный",
};

// ✅ Цвета бейджей для типов разделов
export const SECTION_TYPE_BADGE_CLASSES: Record<string, string> = {
  platform:
    "bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300",
  tenant_default:
    "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
  custom:
    "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300",
};