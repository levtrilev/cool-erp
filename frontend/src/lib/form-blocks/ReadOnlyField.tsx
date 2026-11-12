// Группа полей только для чтения
// frontend/src/lib/form-blocks/ReadOnlyField.tsx
import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export interface ReadOnlyFieldProps {
  /** Подпись поля. */
  label: string;
  /** Значение: строка, число, boolean или готовый ReactNode. */
  value?: ReactNode;
  /** Текст при пустом значении (null / undefined / ""). */
  fallback?: string;
  /** Пояснение под значением. */
  hint?: string;
  /** Иконка рядом с подписью. */
  icon?: LucideIcon;
  className?: string;
  /** Дополнительные классы блока значения. */
  valueClassName?: string;
}

const isEmptyValue = (value: ReactNode): boolean =>
  value === null || value === undefined || value === "";

/**
 * Поле только для чтения: подпись + значение в рамке (тип readonly_display
 * из cool-erp-form v1.2 §2.10). Не является элементом формы и не участвует
 * в состоянии RHF. Пустые значения показываются приглушённым fallback.
 * boolean отображается как «Да» / «Нет», число 0 — как «0».
 */
export const ReadOnlyField = ({
  label,
  value,
  fallback = "—",
  hint,
  icon: Icon,
  className,
  valueClassName,
}: ReadOnlyFieldProps) => {
  const empty: boolean = isEmptyValue(value);

  const display: ReactNode = empty
    ? fallback
    : typeof value === "boolean"
      ? value
        ? "Да"
        : "Нет"
      : value;

  const title: string | undefined =
    typeof value === "string" && value !== "" ? value : undefined;

  return (
    <div className={cn("space-y-1.5", className)}>
      <div className="flex items-center gap-1.5 text-sm font-medium leading-none">
        {Icon ? (
          <Icon className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
        ) : null}
        <span className="truncate">{label}</span>
      </div>

      <div
        className={cn(
          "min-h-9 w-full whitespace-pre-wrap break-words rounded-md border border-input bg-muted/40 px-3 py-2 text-sm",
          empty ? "italic text-muted-foreground" : "text-foreground",
          valueClassName,
        )}
        title={title}
      >
        {display}
      </div>

      {hint ? <p className="text-xs text-muted-foreground">{hint}</p> : null}
    </div>
  );
};