// Одно поле (метка + контроллер + ошибка)

import type { ReactNode } from "react";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

export interface FieldBlockProps {
  /** Метка поля. */
  label: string;
  /** Обязательное ли поле (добавляет красный `*`). */
  required?: boolean;
  /** Текст ошибки валидации (Правило №41, п.3). */
  error?: string;
  /** Подсказка под полем (показывается, если нет ошибки). */
  hint?: string;
  /** `id` контрола для связи с `Label` через `htmlFor`. */
  htmlFor?: string;
  /** Сам контрол (обычно обёрнутый в `Controller`). */
  children: ReactNode;
  /** Дополнительные классы для обёртки. */
  className?: string;
}

/**
 * Строительный блок: одно поле формы.
 *
 * Рендерит метку, контрол и ошибку/подсказку.
 * Не управляет состоянием — только презентация.
 * Используется внутри `FieldsGrid` или самостоятельно.
 */
export const FieldBlock = ({
  label,
  required = false,
  error,
  hint,
  htmlFor,
  children,
  className,
}: FieldBlockProps) => (
  <div className={cn("space-y-2", className)}>
    <Label htmlFor={htmlFor}>
      {label}
      {required && <span className="text-destructive"> *</span>}
    </Label>
    {children}
    {/* Ошибка приоритетнее подсказки (Правило №41, п.3) */}
    {error ? (
      <p className="text-xs text-destructive">{error}</p>
    ) : hint ? (
      <p className="text-xs text-muted-foreground">{hint}</p>
    ) : null}
  </div>
);