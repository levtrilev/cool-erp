import { useState } from "react";
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

export interface ReferenceMultiItem {
  id: string;
  name: string;
  [key: string]: unknown;
}

interface ReferenceMultiSelectProps<T extends ReferenceMultiItem> {
  fetchFn: (params: {
    skip: number;
    limit: number;
    search?: string;
  }) => Promise<{ items: T[]; total: number }>;
  queryKey: string[];
  value: string[];
  onValueChange: (value: string[]) => void;
  placeholder?: string;
  disabled?: boolean;
  limit?: number;
  heading?: string;
  columns?: Array<{ column: keyof T; label: string }>;
  /** Элементы, которые уже выбраны (для отображения названий) */
  selectedItems?: Array<{ id: string; name: string }>;
  /** Элементы, которые нужно исключить из списка (например, уже назначенные) */
  excludeIds?: string[];
}

/**
 * Компонент множественного выбора из справочника.
 * Показывает dropdown с поиском и чекбоксами.
 * НЕ отображает chips — для этого используйте MultiSelectChips.
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
//   selectedItems = [],
  excludeIds = [],
}: ReferenceMultiSelectProps<T>) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: [...queryKey, search],
    queryFn: () => fetchFn({ skip: 0, limit, search: search || undefined }),
    enabled: open,
  });

  // Фильтруем элементы, исключая уже выбранные и те, что в excludeIds
  const items = (data?.items ?? []).filter(
    (item) => !excludeIds.includes(item.id)
  );

//   const selectedItemsMap = new Map(
//     selectedItems.map((item) => [item.id, item.name])
//   );

  const handleSelect = (itemId: string) => {
    if (value.includes(itemId)) {
      onValueChange(value.filter((id) => id !== itemId));
    } else {
      onValueChange([...value, itemId]);
    }
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className={cn(
            "w-full justify-between",
            value.length === 0 && "text-muted-foreground"
          )}
          disabled={disabled}
        >
          <span>
            {value.length > 0
              ? `Выбрано: ${value.length}`
              : placeholder}
          </span>
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