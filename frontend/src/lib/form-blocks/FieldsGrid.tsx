// Сетка полей (2 колонки)
// Обёртка над grid для расположения полей в 1–3 колонки. 
// Обеспечивает единообразие отступов во всех формах.

import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export interface FieldsGridProps {
  /** Число колонок (1, 2 или 3). По умолчанию 2. */
  cols?: 1 | 2 | 3;
  children: ReactNode;
  className?: string;
}

/** Маппинг числа колонок на Tailwind-классы. */
const COLS_CLASS: Record<1 | 2 | 3, string> = {
  1: "grid-cols-1",
  2: "grid-cols-2",
  3: "grid-cols-3",
};

/**
 * Строительный блок: сетка полей формы.
 *
 * Группирует `FieldBlock` в колонки с единым шагом.
 * Заменяет ручные `<div className="grid grid-cols-2 gap-4">`.
 */
export const FieldsGrid = ({ cols = 2, children, className }: FieldsGridProps) => (
  <div className={cn("grid gap-4", COLS_CLASS[cols], className)}>
    {children}
  </div>
);