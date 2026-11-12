// Обёртка таблицы с заголовком
// Обёртка для табличных частей формы: заголовок, опциональные действия, 
// состояние загрузки. Используется для черновых таблиц (строки заказа, платежи и т.д.).
import type { ReactNode } from "react";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

export interface TableSectionProps {
  /** Заголовок секции (например, «Строки заказа»). */
  title: string;
  /** Пояснение под заголовком. */
  description?: string;
  /** Кнопки/действия справа от заголовка (добавить строку и т.д.). */
  actions?: ReactNode;
  /** Показывать спиннер вместо контента (Правило №38). */
  isLoading?: boolean;
  /** Контент секции (обычно таблица или черновая таблица). */
  children: ReactNode;
  className?: string;
}

/**
 * Строительный блок: секция с таблицей внутри формы.
 *
 * Обеспечивает единообразное оформление табличных частей:
 * заголовок, действия, спиннер при загрузке.
 */
export const TableSection = ({
  title,
  description,
  actions,
  isLoading = false,
  children,
  className,
}: TableSectionProps) => (
  <section className={cn("space-y-2", className)}>
    <div className="flex items-center justify-between gap-2">
      <div>
        <h3 className="text-sm font-medium leading-none">{title}</h3>
        {description && (
          <p className="text-xs text-muted-foreground mt-1">{description}</p>
        )}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>

    {isLoading ? (
      <div className="flex items-center justify-center h-32 border rounded-md">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    ) : (
      children
    )}
  </section>
);