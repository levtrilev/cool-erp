// frontend/src/lib/form-blocks/FormTabs.tsx
import {
  Children,
  isValidElement,
  type ReactElement,
  type ReactNode,
} from "react";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import { cn } from "@/lib/utils";

export interface FormTabPanelProps {
  /** Уникальный идентификатор вкладки (значение TabsContent). */
  value: string;
  /** Подпись на переключателе вкладок. */
  label: string;
  className?: string;
  children: ReactNode;
}

/**
 * Декларация вкладки формы: метка уходит в переключатель,
 * содержимое — в область контента. Рендерится компонентом FormTabs;
 * самостоятельно ничего не выводит.
 */
export const FormTabPanel = ({ children }: FormTabPanelProps) => (
  <>{children}</>
);

export interface FormTabsProps {
  /** Вкладка, открытая по умолчанию. */
  defaultValue: string;
  className?: string;
  children: ReactNode;
}

/**
 * Вкладки документной формы.
 *
 * ✅ Стабильная высота: все панели монтируются постоянно (forceMount) и
 * укладываются в ОДНУ ячейку grid (col-start-1 row-start-1). Неактивная
 * панель скрывается через visibility (data-[state=inactive]:invisible),
 * а не через display — поэтому она продолжает задавать высоту области.
 * Высота контента = высота самой высокой вкладки и не меняется при
 * переключении: окно документа не «прыгает», переключатель остаётся
 * вверху, а на короткой вкладке ниже контента остаётся пустое место
 * до футера с кнопками.
 */
export const FormTabs = ({
  defaultValue,
  className,
  children,
}: FormTabsProps) => {
  const panels = Children.toArray(children).filter(
    (child): child is ReactElement<FormTabPanelProps> =>
      isValidElement(child) && child.type === FormTabPanel,
  );

  return (
    <Tabs defaultValue={defaultValue} className={className}>
      <TabsList>
        {panels.map((panel) => (
          <TabsTrigger
            key={panel.props.value}
            value={panel.props.value}
            className="cursor-pointer"
          >
            {panel.props.label}
          </TabsTrigger>
        ))}
      </TabsList>

      {/* Одна ячейка grid на все панели: высота области постоянна. */}
      <div className="grid min-h-0">
        {panels.map((panel) => (
          <TabsContent
            key={panel.props.value}
            value={panel.props.value}
            forceMount
            className={cn(
              "col-start-1 row-start-1",
              // visibility, а не display: скрытая панель сохраняет место
              // в раскладке и не участвует в фокусе/доступности.
              "data-[state=inactive]:invisible",
              panel.props.className,
            )}
          >
            {panel.props.children}
          </TabsContent>
        ))}
      </div>
    </Tabs>
  );
};