import { useState, useEffect, useMemo, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  X,
  Plus,
  Check,
  //   Loader2,
  ChevronLeft,
  ChevronRight,
  ChevronsRight,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
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

interface ReferenceMultiSelectChipsProps<T extends ReferenceMultiItem> {
  fetchFn: (params: {
    skip: number;
    limit: number;
    search?: string;
  }) => Promise<{ items: T[]; total: number }>;
  queryKey: string[];
  value: string[];
  onValueChange: (value: string[]) => void;
  /** Все доступные элементы — для отображения названий в чипсах */
  allItems: Array<{ id: string; name: string }>;
  newItemIds?: string[];
  placeholder?: string;
  disabled?: boolean;
  limit?: number;
  heading?: string;
  columns?: ReferenceMultiColumn[];
}

/**
 * Компонент множественного выбора в виде чипсов.
 *
 * Визуальное представление:
 * - Выбранные элементы отображаются как чипсы с кнопкой удаления (x)
 * - Последний "чипс" — кнопка "+", открывающая окно мультивыбора
 *
 * Окно мультивыбора:
 * - Используется ТОЛЬКО для добавления новых элементов
 * - Ранее выбранные элементы НЕ отображаются в списке (исключены)
 * - Ранее выбранные элементы НЕ отмечаются чекбоксами (их нет в списке)
 * - Элементы, выбираемые в текущей сессии, отмечаются чекбоксом
 * - Кнопка "Готово" добавляет выбранные элементы как чипсы
 */
export function ReferenceMultiSelectChips<T extends ReferenceMultiItem>({
  fetchFn,
  queryKey,
  value,
  onValueChange,
  allItems,
  newItemIds,
  placeholder = "Добавить...",
  disabled = false,
  limit = 50,
  heading = "Выберите элементы",
  columns,
}: ReferenceMultiSelectChipsProps<T>) {
  // ==========================================
  // СОСТОЯНИЕ
  // ==========================================
  const [open, setOpen] = useState(false);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [selectedIndex, setSelectedIndex] = useState(0);
  /** Временный выбор в текущей сессии добавления (ещё не в value) */
  const [tempSelection, setTempSelection] = useState<string[]>([]);

  const fetchFnRef = useRef(fetchFn);
  useEffect(() => {
    fetchFnRef.current = fetchFn;
  }, [fetchFn]);

  const hasColumns = columns && columns.length > 0;
  const columnsLength = columns?.length ?? 0;

  // ==========================================
  // ПОИСК С DEBOUNCE (как в ReferenceSelect)
  // ==========================================
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput);
      setPage(1);
      setSelectedIndex(0);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchInput]);

  // ==========================================
  // ЗАГРУЗКА ДАННЫХ
  // ==========================================
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

  // ✅ Исключаем уже выбранные элементы из списка (окно только для добавления)
  const items = useMemo(() => {
    const all = data?.items ?? [];
    return all.filter((item) => !value.includes(item.id));
  }, [data?.items, value]);

  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / limit);

  // ==========================================
  // ЧИПСЫ ВЫБРАННЫХ ЭЛЕМЕНТОВ
  // ==========================================
  const selectedItems = useMemo(
    () => allItems.filter((item) => value.includes(item.id)),
    [allItems, value],
  );

  // ==========================================
  // ОБРАБОТЧИКИ
  // ==========================================

  /** Удаление чипса */
  const handleRemove = (itemId: string) => {
    onValueChange(value.filter((id) => id !== itemId));
  };

  /** Открытие окна мультивыбора */
  const handleOpen = () => {
    setOpen(true);
    setTempSelection([]);
    setSearchInput("");
    setSearch("");
    setPage(1);
    setSelectedIndex(0);
  };

  /** Закрытие окна мультивыбора (без сохранения) */
  const handleOpenChange = (isOpen: boolean) => {
    setOpen(isOpen);
    if (!isOpen) {
      setTempSelection([]);
    }
  };

  /** Клик на элемент в списке — добавление/убирание из временного списка */
  const handleToggle = (itemId: string) => {
    if (tempSelection.includes(itemId)) {
      setTempSelection(tempSelection.filter((id) => id !== itemId));
    } else {
      setTempSelection([...tempSelection, itemId]);
    }
  };

  /** Кнопка "Готово" — добавление временного списка к value */
  const handleDone = () => {
    const newValue = [...new Set([...value, ...tempSelection])];
    onValueChange(newValue);
    setOpen(false);
    setTempSelection([]);
  };

  /** Навигация с клавиатуры в списке */
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
      handleOpenChange(false);
    }
  };

  /** Смена страницы */
  const handlePageChange = (newPage: number) => {
    setPage(newPage);
    setSelectedIndex(0);
  };

  // ==========================================
  // ПАГИНАЦИЯ (как в ReferenceSelect)
  // ==========================================
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
      </Button>,
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
        </Button>,
      );
      if (startPage > 2)
        pages.push(
          <span key="dots1" className="px-1 text-muted-foreground">
            ...
          </span>,
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
        </Button>,
      );
    }

    if (endPage < totalPages) {
      if (endPage < totalPages - 1)
        pages.push(
          <span key="dots2" className="px-1 text-muted-foreground">
            ...
          </span>,
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
        </Button>,
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
      </Button>,
    );

    return (
      <div className="flex items-center justify-center gap-1 pt-2 border-t mt-2">
        {pages}
      </div>
    );
  };

  // ==========================================
  // РЕНДЕР
  // ==========================================
  return (
    <div className="space-y-2">
      {/* Чипсы выбранных элементов + кнопка "+" */}
      <div className="flex flex-wrap gap-2 items-center">
        {selectedItems.map((item) => (
          <Badge
            key={item.id}
            variant="secondary"
            className="flex items-center gap-1 pr-1"
          >
            <span className="max-w-[150px] truncate">{item.name}</span>
            {newItemIds?.includes(item.id) && (
              <span className="text-[10px] bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400 px-1.5 py-0.5 rounded-full font-medium uppercase tracking-wide">
                новый
              </span>
            )}
            <button
              type="button"
              className="rounded-full outline-none ring-offset-background focus:ring-2 focus:ring-ring focus:ring-offset-1"
              onClick={() => handleRemove(item.id)}
              disabled={disabled}
              title={`Удалить ${item.name}`}
            >
              <X className="h-3 w-3 text-muted-foreground hover:text-foreground" />
            </button>
          </Badge>
        ))}

        {/* Кнопка "+" как последний чипс */}
        <Popover open={open} onOpenChange={handleOpenChange}>
          <PopoverTrigger asChild>
            <button
              type="button"
              onClick={handleOpen}
              disabled={disabled}
              className={cn(
                "inline-flex items-center gap-1 rounded-md border border-dashed px-2 py-0.5",
                "text-xs font-medium text-muted-foreground",
                "hover:text-foreground hover:border-foreground/50",
                "focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1",
                "transition-colors",
                disabled && "opacity-50 cursor-not-allowed",
              )}
              title={placeholder}
            >
              <Plus className="h-3 w-3" />
              Добавить
            </button>
          </PopoverTrigger>

          <PopoverContent
            className={cn(
              "p-0 overflow-hidden",
              hasColumns
                ? "min-w-[480px] max-w-[90vw]"
                : "w-[--radix-popover-trigger-width]",
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

              {/* Заголовок колонок — идентично ReferenceSelect */}
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
                      const widthClass =
                        columnsLength === 2 ? "w-[140px]" : "w-[240px]";
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
                  // ✅ Отмечаем только элементы из временного списка (текущая сессия)
                  // Ранее выбранные (в value) уже исключены из списка
                  const isTempSelected = tempSelection.includes(item.id);
                  return (
                    <CommandItem
                      key={item.id}
                      value={item.id}
                      className={cn(
                        "cursor-pointer px-3 py-1",
                        index === selectedIndex &&
                          "bg-accent text-accent-foreground",
                      )}
                      onSelect={() => handleToggle(item.id)}
                      onMouseEnter={() => setSelectedIndex(index)}
                    >
                      <Check
                        className={cn(
                          "mr-2 h-4 w-4 shrink-0",
                          isTempSelected ? "opacity-100" : "opacity-0",
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
                              {item[col.column] != null
                                ? String(item[col.column])
                                : "—"}
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

              {/* Кнопка "Готово" — добавляет временный список как чипсы */}
              <div className="border-t p-2 flex justify-end">
                <Button
                  size="sm"
                  onClick={handleDone}
                  disabled={tempSelection.length === 0}
                >
                  Готово ({tempSelection.length})
                </Button>
              </div>
            </Command>
          </PopoverContent>
        </Popover>
      </div>

      {/* Подпись с количеством выбранных */}
      <p className="text-xs text-muted-foreground">Выбрано: {value.length}</p>
    </div>
  );
}
