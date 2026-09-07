import { useState, useEffect, useMemo, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Check,
  ChevronsUpDown,
  Loader2,
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

export interface ReferenceItem {
  id: string;
  name: string;
  [key: string]: unknown;
}

export interface PaginatedReferenceResponse<T extends ReferenceItem> {
  items: T[];
  total: number;
}

export interface ReferenceColumn {
  column: string;
  label: string;
}

export interface ReferenceSelectProps<T extends ReferenceItem> {
  fetchFn: (params: {
    skip: number;
    limit: number;
    search?: string;
  }) => Promise<PaginatedReferenceResponse<T>>;
  queryKey: string[];
  value: string | undefined;
  onValueChange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  limit?: number;
  selectedLabel?: string;
  heading?: string;
  columns?: ReferenceColumn[];
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
}: ReferenceSelectProps<T>) {
  const [open, setOpen] = useState(false);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);

  const [selectedIndex, setSelectedIndex] = useState(0);
  const [localLabel, setLocalLabel] = useState<string | undefined>(undefined);

  // ✅ Ref для fetchFn, чтобы избежать проблем с нестабильными ссылками в useEffect
  const fetchFnRef = useRef(fetchFn);
  useEffect(() => {
    fetchFnRef.current = fetchFn;
  }, [fetchFn]);

  const hasColumns = columns && columns.length > 0;

  const handleOpenChange = (isOpen: boolean) => {
    setOpen(isOpen);
    if (isOpen) {
      setSelectedIndex(0);
    }
  };

  // ✅ НОВОЕ: При открытии справочника с выбранным значением
  // находим страницу, на которой находится этот элемент
  useEffect(() => {
    if (open && value) {
      fetchFnRef
        .current({ limit: 1000, skip: 0 })
        .then((allData) => {
          if (allData?.items) {
            const index = allData.items.findIndex((item) => item.id === value);
            if (index !== -1) {
              const targetPage = Math.floor(index / limit) + 1;
              setPage(targetPage);
              setSelectedIndex(index % limit);
            }
          }
        })
        .catch((error) => {
          console.error("Ошибка поиска страницы элемента:", error);
        });
    }
  }, [open, value, limit]);

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

  const handlePageChange = (newPage: number) => {
    setPage(newPage);
    setSelectedIndex(0);
  };

  const displayLabel = useMemo(() => {
    if (value) {
      if (localLabel) return localLabel;
      const found = items.find((item) => item.id === value);
      if (found) return found.name;
      if (selectedLabel) return selectedLabel;
    }
    return placeholder;
  }, [value, localLabel, items, selectedLabel, placeholder]);

  const handleSelect = (itemId: string) => {
    const selectedItem = items.find((i) => i.id === itemId);
    if (selectedItem) {
      setLocalLabel(selectedItem.name);
    }
    onValueChange(itemId);
    setOpen(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (items.length === 0) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((prev) => {
        const next = Math.min(prev + 1, items.length - 1);
        setTimeout(() => {
          const el = document.getElementById(`cmd-item-${items[next].id}`);
          el?.scrollIntoView({ block: "nearest" });
        }, 0);
        return next;
      });
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((prev) => {
        const next = Math.max(prev - 1, 0);
        setTimeout(() => {
          const el = document.getElementById(`cmd-item-${items[next].id}`);
          el?.scrollIntoView({ block: "nearest" });
        }, 0);
        return next;
      });
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (items[selectedIndex]) {
        handleSelect(items[selectedIndex].id);
      }
    } else if (e.key === "Escape") {
      e.preventDefault();
      setOpen(false);
    }
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

  return (
    <Popover open={open} onOpenChange={handleOpenChange}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className="w-full justify-between font-normal"
          disabled={disabled}
        >
          <span className={cn("truncate", !value && "text-muted-foreground")}>
            {isLoading && !displayLabel ? (
              <span className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" /> Загрузка...
              </span>
            ) : (
              displayLabel
            )}
          </span>
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
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

          {/* ✅ Заголовок колонок — используем CSS Grid для идеального выравнивания */}
          {hasColumns && (
            <div
              className="px-3 py-1 border-b bg-muted/30 text-xs font-medium text-muted-foreground"
              style={{
                display: "grid",
                gridTemplateColumns: `16px 1fr ${columns.map(() => "140px").join(" ")}`,
                gap: "1rem", // gap-4 = 16px
                alignItems: "center",
              }}
            >
              <div /> {/* Placeholder вместо Check */}
              <span className="truncate">Название</span>
              {columns.map((col) => (
                <span key={col.column} className="truncate">
                  {col.label}
                </span>
              ))}
            </div>
          )}

          <CommandList className="max-h-[min(330px,60vh)] overflow-y-auto">
            <CommandEmpty className="py-2 text-center text-sm text-muted-foreground">
              {isLoading ? "Загрузка..." : "Ничего не найдено"}
            </CommandEmpty>

            {items.map((item, index) => (
              <CommandItem
                key={item.id}
                id={`cmd-item-${item.id}`}
                value={item.id}
                className={cn(
                  "cursor-pointer px-3 py-1",
                  index === selectedIndex && "bg-accent text-accent-foreground",
                )}
                // ✅ Используем CSS Grid для строк данных — идентично заголовку
                style={
                  hasColumns
                    ? {
                        display: "grid",
                        gridTemplateColumns: `16px 1fr ${columns.map(() => "140px").join(" ")}`,
                        gap: "1rem",
                        alignItems: "center",
                      }
                    : undefined
                }
                onSelect={() => handleSelect(item.id)}
                onMouseEnter={() => setSelectedIndex(index)}
              >
                <Check
                  className={cn(
                    "h-4 w-4 shrink-0",
                    value === item.id ? "opacity-100" : "opacity-0",
                  )}
                />

                {hasColumns ? (
                  <>
                    <span className="truncate text-sm font-medium">
                      {item.name}
                    </span>
                    {columns.map((col) => (
                      <span
                        key={col.column}
                        className="truncate text-sm text-muted-foreground"
                      >
                        {item[col.column] != null
                          ? String(item[col.column])
                          : "—"}
                      </span>
                    ))}
                  </>
                ) : (
                  <span className="truncate text-sm">{item.name}</span>
                )}
              </CommandItem>
            ))}
          </CommandList>

          {renderPagination()}
        </Command>
      </PopoverContent>
    </Popover>
  );
}
