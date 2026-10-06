import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Check, ChevronsUpDown, Loader2 } from "lucide-react";
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

// ✅ Базовый интерфейс для элементов справочника
export interface ReferenceItem {
  id: string;
  [key: string]: unknown;
}

// ✅ Тип ответа, который возвращают все наши эндпоинты (Правило №4)
interface PaginatedReferenceResponse<T> {
  items: T[];
  total: number;
}

interface ApiResponse<T> {
  success: boolean;
  message: string;
  data?: T;
}

// ✅ Пропсы компонента
interface ReferenceSelectProps<T extends ReferenceItem> {
  // ✅ fetchFn возвращает ApiResponse<PaginatedResponse<T>> — как все наши эндпоинты
  fetchFn: (params: { skip?: number; limit?: number; search?: string }) => Promise<ApiResponse<PaginatedReferenceResponse<T>>>;
  queryKey: string[];
  value: string;
  onValueChange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  limit?: number;
  selectedLabel?: string;
  heading?: string;
  // ✅ Колонки для расширенного отображения
  columns?: Array<{ key: keyof T; label: string }>;
  // ✅ Поле для отображения в списке (по умолчанию "name")
  labelField?: keyof T;
}

export function ReferenceSelect<T extends ReferenceItem>({
  fetchFn,
  queryKey,
  value,
  onValueChange,
  placeholder = "Выберите...",
  disabled = false,
  limit = 10,
  selectedLabel,
  heading,
  columns,
  labelField = "name" as keyof T,
}: ReferenceSelectProps<T>) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");

  // ✅ Загружаем данные через React Query
  const { data, isLoading } = useQuery({
    queryKey: [...queryKey, search, limit],
    queryFn: () => fetchFn({ skip: 0, limit, search: search || undefined }),
    enabled: open, // Загружаем только при открытии попапа
  });

  // ✅ Распаковываем items из response.data.items
  const items = useMemo(() => data?.data?.items || [], [data]);

  // ✅ Находим выбранный элемент для отображения в кнопке
  const selectedItem = useMemo(
    () => items.find((item) => item.id === value),
    [items, value]
  );

  // ✅ Определяем отображаемый текст
  const displayLabel = useMemo(() => {
    if (selectedLabel) return selectedLabel;
    if (selectedItem) return String(selectedItem[labelField] || selectedItem.id);
    return "";
  }, [selectedLabel, selectedItem, labelField]);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          disabled={disabled}
          className="w-full justify-between"
        >
          {displayLabel || placeholder}
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[var(--radix-popover-trigger-width)] p-0" align="start">
        <Command shouldFilter={false}>
          <CommandInput
            placeholder="Поиск..."
            value={search}
            onValueChange={setSearch}
          />
          <CommandList>
            {isLoading ? (
              <div className="flex items-center justify-center py-6">
                <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                <span className="ml-2 text-sm text-muted-foreground">Загрузка...</span>
              </div>
            ) : items.length === 0 ? (
              <CommandEmpty>Ничего не найдено</CommandEmpty>
            ) : (
              <CommandGroup heading={heading}>
                {items.map((item) => (
                  <CommandItem
                    key={item.id}
                    value={String(item[labelField])}
                    onSelect={() => {
                      onValueChange(item.id);
                      setOpen(false);
                      setSearch("");
                    }}
                  >
                    <Check
                      className={cn(
                        "mr-2 h-4 w-4",
                        value === item.id ? "opacity-100" : "opacity-0"
                      )}
                    />
                    {columns ? (
                      // ✅ Расширенное отображение с колонками
                      <div className="flex flex-col">
                        <span className="font-medium">{String(item[labelField])}</span>
                        {columns.map((col) => (
                          <span key={String(col.key)} className="text-xs text-muted-foreground">
                            {col.label}: {String(item[col.key] || "—")}
                          </span>
                        ))}
                      </div>
                    ) : (
                      // ✅ Простое отображение
                      <span>{String(item[labelField])}</span>
                    )}
                  </CommandItem>
                ))}
              </CommandGroup>
            )}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}