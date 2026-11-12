// Вкладки с индикаторами изменений
// Обёртка над Tabs из shadcn. 
// Поддерживает индикаторы несохранённых изменений (*) и счётчики на вкладках (Правило №46, п.7). 
// Метаданные вкладок извлекаются из children (FormTabPanel).

import * as React from "react";
import type { ReactNode, ReactElement } from "react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
// import { cn } from "@/lib/utils";

export interface FormTabPanelProps {
  /** Уникальный идентификатор вкладки. */
  value: string;
  /** Метка вкладки. */
  label: string;
  /** Индикатор несохранённых изменений (жёлтый `*`). */
  dirty?: boolean;
  /** Счётчик в заголовке (например, число строк). */
  counter?: number | string;
  /** Отключить вкладку. */
  disabled?: boolean;
  children: ReactNode;
}

/**
 * Панель вкладки. Сам по себе рендерит только детей;
 * метаданные (label, dirty, counter) читаются родительским `FormTabs`.
 */
export const FormTabPanel = ({ children }: FormTabPanelProps) => <>{children}</>;
FormTabPanel.displayName = "FormTabPanel";

export interface FormTabsProps {
  /** Вкладка по умолчанию (неуправляемый режим). */
  defaultValue?: string;
  /** Активная вкладка (управляемый режим). */
  value?: string;
  /** Колбэк смены вкладки. */
  onValueChange?: (value: string) => void;
  children: ReactNode;
  className?: string;
}

/**
 * Строительный блок: вкладки формы с индикаторами изменений.
 *
 * Извлекает метаданные из дочерних `FormTabPanel` и строит
 * `TabsList` с триггерами. Поддерживает `dirty` (жёлтый `*`)
 * и `counter` (число в скобках) на каждой вкладке.
 */
export const FormTabs = ({
  defaultValue,
  value,
  onValueChange,
  children,
  className,
}: FormTabsProps) => {
  // Извлекаем только дочерние элементы типа FormTabPanel
  const panels = React.Children.toArray(children).filter(
    (child): child is ReactElement<FormTabPanelProps> =>
      React.isValidElement(child) && child.type === FormTabPanel,
  );

  return (
    <Tabs
      defaultValue={defaultValue}
      value={value}
      onValueChange={onValueChange}
      className={className}
    >
      <TabsList className="w-full justify-start h-auto flex-wrap">
        {panels.map((panel) => {
          const { value: tabValue, label, dirty, counter, disabled } = panel.props;
          return (
            <TabsTrigger
              key={tabValue}
              value={tabValue}
              disabled={disabled}
              className="relative"
            >
              {label}
              {counter !== undefined && (
                <span className="ml-1 text-muted-foreground">({counter})</span>
              )}
              {/* Индикатор несохранённых изменений (Правило №46, п.7.5) */}
              {dirty && (
                <span className="absolute -top-1 -right-1 text-amber-500 text-xl font-bold leading-none">
                  *
                </span>
              )}
            </TabsTrigger>
          );
        })}
      </TabsList>

      {panels.map((panel) => (
        <TabsContent key={panel.props.value} value={panel.props.value} className="mt-4">
          {panel.props.children}
        </TabsContent>
      ))}
    </Tabs>
  );
};