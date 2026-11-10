import { z } from "zod";

/** Формат тега (ТЗ §6.2): <пространство>:<значение>, без пробелов. */
export const tagPattern = /^[^\s:]+:[^\s:]+$/;

/**
 * Разбирает строку тегов в массив. Разделители — запятая и перевод строки.
 */
export const parseTags = (value: string): string[] =>
  value
    .split(/[,\n]/)
    .map((item) => item.trim())
    .filter((item) => item.length > 0);

/**
 * Склеивает массив тегов в строку через запятую для отображения в Input.
 */
export const joinTags = (tags: string[] | undefined): string =>
  (tags ?? []).join(", ");

/**
 * Безопасный маппинг значения одного строкового enum в другой по значению.
 *
 * Оба enum содержат идентичный набор строковых значений (контракт DocStatus),
 * но являются разными номинальными типами после генерации Orval 8.x.
 * Сопоставление по значениям через String() исключает приведения типов
 * (Правило №44) и не зависит от регистра имён членов enum.
 *
 * @template TTo — целевой номинальный тип enum.
 */
export function mapEnumByValue<TTo extends string>(
  value: string,
  targetEnum: Record<string, TTo>,
): TTo {
  const target = Object.values(targetEnum).find(
    (candidate) => String(candidate) === String(value),
  );
  if (target === undefined) {
    throw new Error(
      `Значение статуса "${value}" отсутствует в целевом справочнике`,
    );
  }
  return target;
}

/**
 * Общие метки статусов документа (контракт DocStatus, единый для всех типов).
 * Перенесено из `notes/schemas.ts`, так как метки одинаковы для всех документов.
 */
export const DOC_STATUS_LABELS: Record<string, string> = {
  draft: "Черновик",
  pending: "На утверждении",
  approved: "Утверждён",
  active: "Действует",
  archived: "Архив",
};

/** Zod-валидатор массива тегов. Переиспользуется в схемах документов. */
export const tagsArraySchema = z.array(
  z.string().regex(tagPattern, "Формат тега: пространство:значение"),
);