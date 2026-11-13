// Группа полей только для чтения
// frontend/src/lib/form-blocks/ReadOnlyGroup.tsx
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

const COLUMN_CLASS: Record<1 | 2 | 3, string> = {
  1: "grid-cols-1",
  2: "grid-cols-1 sm:grid-cols-2",
  3: "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3",
};

export interface ReadOnlyGroupProps {
  /** Заголовок группы (опционально). */
  title?: string;
  /** Пояснение под заголовком. */
  description?: string;
  /** Колонок в сетке полей (адаптивно). */
  columns?: 1 | 2 | 3;
  className?: string;
  children: ReactNode;
}

/**
 * Группа полей только для чтения: приглушённый контейнер с сеткой
 * ReadOnlyField. Визуально отделяет read-only блок от редактируемых
 * секций формы. Может использоваться самостоятельно или внутри FormSection.
 */
export const ReadOnlyGroup = ({
  title,
  description,
  columns = 2,
  className,
  children,
}: ReadOnlyGroupProps) => {
  const hasHeader: boolean = Boolean(title ?? description);

  return (
    <div
      className={cn(
        "space-y-3 rounded-md border bg-muted/20 p-4",
        className,
      )}
    >
      {hasHeader ? (
        <div className="space-y-1 border-b pb-2">
          {title ? (
            <h3 className="text-sm font-semibold leading-none">{title}</h3>
          ) : null}
          {description ? (
            <p className="text-xs text-muted-foreground">{description}</p>
          ) : null}
        </div>
      ) : null}

      <div className={cn("grid gap-4", COLUMN_CLASS[columns])}>{children}</div>
    </div>
  );
};