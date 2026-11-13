// Именованная секция с разделителем
// frontend/src/lib/form-blocks/FormSection.tsx
import { useId, useState, type ReactNode } from "react";
import { ChevronDown, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

const COLUMN_CLASS: Record<1 | 2 | 3, string> = {
  1: "grid-cols-1",
  2: "grid-cols-1 sm:grid-cols-2",
  3: "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3",
};

export interface FormSectionProps {
  /** Заголовок секции. */
  title: string;
  /** Пояснение под заголовком. */
  description?: string;
  /** Иконка рядом с заголовком. */
  icon?: LucideIcon;
  /** Колонок в сетке полей (адаптивно). */
  columns?: 1 | 2 | 3;
  /** Секцию можно свернуть. */
  collapsible?: boolean;
  /** Начальное состояние сворачиваемой секции. */
  defaultOpen?: boolean;
  className?: string;
  /** Дополнительные классы сетки полей. */
  contentClassName?: string;
  children: ReactNode;
}

/**
 * Секция формы: заголовок + адаптивная сетка полей.
 * Размещается внутри FormTabPanel для логической группировки полей.
 * Кнопка сворачивания имеет type="button" и не отправляет форму.
 * Состояние свёрнутости — локальное UI-состояние, данные формы не затрагивает.
 */
export const FormSection = ({
  title,
  description,
  icon: Icon,
  columns = 1,
  collapsible = false,
  defaultOpen = true,
  className,
  contentClassName,
  children,
}: FormSectionProps) => {
  const [open, setOpen] = useState<boolean>(defaultOpen);
  const contentId: string = useId();
  const isOpen: boolean = !collapsible || open;

  const header: ReactNode = (
    <>
      {Icon ? <Icon className="h-4 w-4 shrink-0 text-muted-foreground" /> : null}
      <div className="min-w-0 flex-1">
        <h3 className="text-sm font-semibold leading-none">{title}</h3>
        {description ? (
          <p className="mt-1 text-xs text-muted-foreground">{description}</p>
        ) : null}
      </div>
    </>
  );

  return (
    <section className={cn("space-y-3", className)}>
      {collapsible ? (
        <button
          type="button"
          onClick={() => setOpen((value) => !value)}
          aria-expanded={isOpen}
          aria-controls={contentId}
          className="flex w-full items-center gap-2 rounded-sm border-b pb-2 text-left transition-colors hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
        >
          {header}
          <ChevronDown
            className={cn(
              "h-4 w-4 shrink-0 text-muted-foreground transition-transform duration-200",
              isOpen && "rotate-180",
            )}
          />
        </button>
      ) : (
        <div className="flex items-center gap-2 border-b pb-2">{header}</div>
      )}

      <div
        id={contentId}
        className={cn(
          "gap-4",
          isOpen ? cn("grid", COLUMN_CLASS[columns]) : "hidden",
          contentClassName,
        )}
      >
        {children}
      </div>
    </section>
  );
};