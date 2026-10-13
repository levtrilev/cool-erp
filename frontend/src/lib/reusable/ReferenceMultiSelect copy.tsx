import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Check, X, ChevronsUpDown, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Badge } from "@/components/ui/badge";

/**
 * Базовый интерфейс для элементов справочника.
 * Правило №27: id и name обязательны.
 */
export interface ReferenceMultiItem {
  id: string;
  name: string;
  [key: string]: unknown;
}

interface ReferenceMultiSelectProps<T extends ReferenceMultiItem> {
  /**
   * Функция загрузки данных из API.
   * Должна возвращать { items, total } по аналогии с ReferenceSelect.
   */
  fetchFn: (params: {
    skip: number;
    limit: number;
    search?: string;
  }) => Promise<{ items: T[]; total: number }>;

  /** Ключ для React Query кэша */
  queryKey: string[];

  /** Массив выбранных ID */
  value: string[];

  /** Callback при изменении выбора */
  onValueChange: (value: string[]) => void;

  /** Placeholder для поля ввода */
  placeholder?: string;

  /** Отключить компонент */
  disabled?: boolean;

  /** Лимит элементов на страницу */
  limit?: number;

  /** Заголовок выпадающего списка */
  heading?: string;

  /**
   * Колонки для отображения в таблице результатов.
   * Правило №27: использовать ключ "column", не "key"!
   */
  columns?: Array<{ column: keyof T; label: string }>;

  /**
   * Массив уже выбранных элементов для отображения их названий.
   * Аналог selectedLabel из ReferenceSelect, но для массива.
   */
  selectedItems?: Array<{ id: string; name: string }>;
}

/**
 * Универсальный компонент множественного выбора из справочника.
 * Выбранные элементы отображаются как теги (chips) с кнопкой удаления "×".
 * 
 * Правило №27: Не изменять ReferenceSelect.tsx, создавать отдельные компоненты.
 * Правило №9: Использовать Orval-хуки через fetchFn.
 */
export function ReferenceMultiSelect<T extends ReferenceMultiItem>({
  fetchFn,
  queryKey,
  value,
  onValueChange,
  placeholder = "Выберите...",
  disabled = false,
  limit = 50,
  heading = "Выберите элементы",
  columns = [],
  selectedItems = [],
}: ReferenceMultiSelectProps<T>) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");

  // Загрузка данных из API
  const { data, isLoading } = useQuery({
    queryKey: [...queryKey, search],
    queryFn: () => fetchFn({ skip: 0, limit, search: search || undefined }),
    enabled: open,
  });

  const items = data?.items ?? [];

  // Создаём Map для быстрого поиска названий выбранных элементов
  const selectedItemsMap = new Map(selectedItems.map((item) => [item.id, item.name]));

  const handleSelect = (itemId: string) => {
    if (value.includes(itemId)) {
      // Убираем из выбора
      onValueChange(value.filter((id) => id !== itemId));
    } else {
      // Добавляем в выбор
      onValueChange([...value, itemId]);
    }
  };

  const handleRemove = (itemId: string, e: React.MouseEvent) => {
    e.stopPropagation(); // Предотвращаем открытие popover
    onValueChange(value.filter((id) => id !== itemId));
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className={cn(
            "w-full min-h-[40px] h-auto justify-between flex-wrap gap-1",
            value.length === 0 && "text-muted-foreground"
          )}
          disabled={disabled}
        >
          <div className="flex flex-wrap gap-1 flex-1">
            {value.length === 0 ? (
              <span>{placeholder}</span>
            ) : (
              value.map((itemId) => {
                const itemName = selectedItemsMap.get(itemId) || itemId;
                return (
                  <Badge
                    key={itemId}
                    variant="secondary"
                    className="flex items-center gap-1 pr-1"
                  >
                    <span className="max-w-[150px] truncate">{itemName}</span>
                    <button
                      type="button"
                      className="rounded-full outline-none ring-offset-background focus:ring-2 focus:ring-ring focus:ring-offset-1"
                      onClick={(e) => handleRemove(itemId, e)}
                    >
                      <X className="h-3 w-3 text-muted-foreground hover:text-foreground" />
                    </button>
                  </Badge>
                );
              })
            )}
          </div>
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[--radix-popover-trigger-width] p-0" align="start">
        <Command shouldFilter={false}>
          <CommandInput
            placeholder="Поиск..."
            value={search}
            onValueChange={setSearch}
          />
          <CommandList>
            {isLoading && (
              <div className="flex items-center justify-center py-6">
                <Loader2 className="h-4 w-4 animate-spin" />
              </div>
            )}
            <CommandEmpty>Ничего не найдено.</CommandEmpty>
            <CommandGroup heading={heading}>
              {items.map((item) => {
                const isSelected = value.includes(item.id);
                return (
                  <CommandItem
                    key={item.id}
                    value={item.id}
                    onSelect={() => handleSelect(item.id)}
                  >
                    <Check
                      className={cn(
                        "mr-2 h-4 w-4",
                        isSelected ? "opacity-100" : "opacity-0"
                      )}
                    />
                    <div className="flex-1">
                      <div className="font-medium">{item.name}</div>
                      {columns.length > 0 && (
                        <div className="text-xs text-muted-foreground">
                          {columns
                            .map((col) => {
                              const val = item[col.column];
                              return typeof val === "string" ? val : "";
                            })
                            .filter(Boolean)
                            .join(" • ")}
                        </div>
                      )}
                    </div>
                  </CommandItem>
                );
              })}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}