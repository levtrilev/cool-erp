import { useState, useEffect, useMemo, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Check,
  ChevronsUpDown,
  // Loader2,
  ChevronLeft,
  ChevronRight,
  ChevronsRight,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
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

export interface ReferenceMultiColumn {
  column: string;
  label: string;
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
  columns?: ReferenceMultiColumn[];
  /** Названия выбранных элементов для отображения в триггере */
  selectedLabels?: string[];
}

/**
 * Компонент множественного выбора из справочника.
 * Визуально идентичен ReferenceSelect: тот же триггер, колонки, пагинация.
 * Отличие: мультивыбор с чекбоксами и кнопка "Готово" для закрытия.
 */
export function ReferenceMultiSelect<T extends ReferenceMultiItem>({
  fetchFn,
  queryKey,
  value,
  onValueChange,
  placeholder = "Выберите...",
  disabled = false,
  limit = 10,
  heading,
  columns,
  selectedLabels,
}: ReferenceMultiSelectProps<T>) {
  const [open, setOpen] = useState(false);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [selectedIndex, setSelectedIndex] = useState(0);

  const fetchFnRef = useRef(fetchFn);
  useEffect(() => {
    fetchFnRef.current = fetchFn;
  }, [fetchFn]);

  const hasColumns = columns && columns.length > 0;
  const columnsLength = columns?.length ?? 0;

  // Debounce поиска (как в ReferenceSelect)
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput);
      setPage(1);
      setSelectedIndex(0);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchInput]);

  const { data, isLoading } = useQuery({
    queryKey: [...queryKey, page, search],
    queryFn: () =>
      fetchFn({
        skip: (page - 1) * limit,
        limit,
        search: search || undefined,
      }),
    staleTime: 5 * 60 * 1000,
    enabled: open,
  });

  const items = useMemo(() => data?.items ?? [], [data?.items]);
  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / limit);

  // Отображаемое имя в триггере
  const displayLabel = useMemo(() => {
    if (value.length === 0) return placeholder;
    if (selectedLabels && selectedLabels.length > 0) {
      return selectedLabels.join(", ");
    }
    return `Выбрано: ${value.length}`;
  }, [value, selectedLabels, placeholder]);

  const handleToggle = (itemId: string) => {
    if (value.includes(itemId)) {
      onValueChange(value.filter((id) => id !== itemId));
    } else {
      onValueChange([...value, itemId]);
    }
    // ✅ Не закрываем поповер — продолжаем мультивыбор
  };

  const handleDone = () => {
    setOpen(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (items.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((prev) => Math.min(prev + 1, items.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((prev) => Math.max(prev - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (items[selectedIndex]) {
        handleToggle(items[selectedIndex].id);
      }
    } else if (e.key === "Escape") {
      e.preventDefault();
      setOpen(false);
    }
  };

  const handlePageChange = (newPage: number) => {
    setPage(newPage);
    setSelectedIndex(0);
  };

  const renderPagination = () => {
    if (totalPages <= 1) return null;
    const pages: React.ReactNode[] = [];
    const maxVisible = 5;
    let startPage = Math.max(1, page - Math.floor(maxVisible / 2));
    const endPage = Math.min(totalPages, startPage + maxVisible - 1);
    if (endPage - startPage + 1 < maxVisible) {
      startPage = Math.max(1, endPage - maxVisible + 1);
    }

    pages.push(
      <Button
        key="prev"
        size="sm"
        variant="outline"
        className="h-8 w-8 p-0"
        disabled={page === 1}
        onClick={() => handlePageChange(Math.max(1, page - 1))}
      >
        <ChevronLeft className="h-4 w-4" />
      </Button>
    );

    if (startPage > 1) {
      pages.push(
        <Button
          key="first"
          size="sm"
          variant="outline"
          className="h-8 w-8 p-0"
          onClick={() => handlePageChange(1)}
        >
          1
        </Button>
      );
      if (startPage > 2)
        pages.push(
          <span key="dots1" className="px-1 text-muted-foreground">
            ...
          </span>
        );
    }

    for (let i = startPage; i <= endPage; i++) {
      pages.push(
        <Button
          key={i}
          size="sm"
          variant={page === i ? "default" : "outline"}
          className="h-8 w-8 p-0"
          onClick={() => handlePageChange(i)}
        >
          {i}
        </Button>
      );
    }

    if (endPage < totalPages) {
      if (endPage < totalPages - 1)
        pages.push(
          <span key="dots2" className="px-1 text-muted-foreground">
            ...
          </span>
        );
      pages.push(
        <Button
          key="last"
          size="sm"
          variant="outline"
          className="h-8 px-2"
          onClick={() => handlePageChange(totalPages)}
        >
          End <ChevronsRight className="h-3 w-3 ml-1" />
        </Button>
      );
    }

    pages.push(
      <Button
        key="next"
        size="sm"
        variant="outline"
        className="h-8 w-8 p-0"
        disabled={page === totalPages}
        onClick={() => handlePageChange(Math.min(totalPages, page + 1))}
      >
        <ChevronRight className="h-4 w-4" />
      </Button>
    );

    return (
      <div className="flex items-center justify-center gap-1 pt-2 border-t mt-2">
        {pages}
      </div>
    );
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        {/* ✅ Триггер идентичен ReferenceSelect */}
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className="w-full justify-between font-normal"
          disabled={disabled}
        >
          <span className={cn("truncate", value.length === 0 && "text-muted-foreground")}>
            {displayLabel}
          </span>
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>

      <PopoverContent
        className={cn(
          "p-0 overflow-hidden",
          hasColumns ? "min-w-[480px] max-w-[90vw]" : "w-[--radix-popover-trigger-width]"
        )}
        align="start"
        sideOffset={4}
      >
        <Command shouldFilter={false} className="min-h-[240px]">
          {heading && (
            <div className="px-3 py-1.5 border-b font-medium text-sm bg-muted/50">
              {heading}
            </div>
          )}
          <CommandInput
            placeholder="Поиск по названию..."
            value={searchInput}
            onValueChange={setSearchInput}
            className="h-8 border-0 focus-visible:ring-0 pl-3"
            onKeyDown={handleKeyDown}
          />

          {/* ✅ Заголовок колонок — идентично ReferenceSelect */}
          {hasColumns && (
            <div className="flex items-center px-3 py-1 border-b bg-muted/30 text-xs font-medium text-muted-foreground">
              <div className="w-6 mr-2 shrink-0" />
              <div className="flex-1 flex items-center gap-4 min-w-0">
                {columnsLength === 1 && (
                  <span className="w-[236px] shrink-0">Название</span>
                )}
                {columnsLength === 2 && (
                  <span className="w-[80px] shrink-0">Название</span>
                )}
                {columns!.map((col) => {
                  const widthClass = columnsLength === 2 ? "w-[140px]" : "w-[240px]";
                  return (
                    <span
                      key={col.column}
                      className={`${widthClass} shrink-0 truncate`}
                    >
                      {col.label}
                    </span>
                  );
                })}
              </div>
            </div>
          )}

          <CommandList className="max-h-[min(330px,60vh)] overflow-y-auto">
            <CommandEmpty className="py-2 text-center text-sm text-muted-foreground">
              {isLoading ? "Загрузка..." : "Ничего не найдено"}
            </CommandEmpty>
            {items.map((item, index) => {
              const isSelected = value.includes(item.id);
              return (
                <CommandItem
                  key={item.id}
                  value={item.id}
                  className={cn(
                    "cursor-pointer px-3 py-1",
                    index === selectedIndex && "bg-accent text-accent-foreground"
                  )}
                  onSelect={() => handleToggle(item.id)}
                  onMouseEnter={() => setSelectedIndex(index)}
                >
                  {/* ✅ Чекбокс — заполненный для выбранных */}
                  <Check
                    className={cn(
                      "mr-2 h-4 w-4 shrink-0",
                      isSelected ? "opacity-100" : "opacity-0"
                    )}
                  />
                  {hasColumns ? (
                    <div className="flex-1 flex items-center gap-4 min-w-0">
                      <span className="flex-1 truncate text-sm font-medium">
                        {item.name}
                      </span>
                      {columns!.map((col) => (
                        <span
                          key={col.column}
                          className="w-[140px] shrink-0 truncate text-sm text-muted-foreground"
                        >
                          {item[col.column] != null ? String(item[col.column]) : "—"}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <span className="truncate text-sm">{item.name}</span>
                  )}
                </CommandItem>
              );
            })}
          </CommandList>

          {renderPagination()}

          {/* ✅ Кнопка "Готово" — закрывает поповер после мультивыбора */}
          <div className="border-t p-2 flex justify-end">
            <Button size="sm" onClick={handleDone}>
              Готово ({value.length})
            </Button>
          </div>
        </Command>
      </PopoverContent>
    </Popover>
  );
}