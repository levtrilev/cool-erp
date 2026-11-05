import { useState, useMemo, useCallback } from "react";
import {
  ArrowUp,
  ArrowDown,
  Filter,
  FilterX,
  ArrowDownUp,
} from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

// ============================================================
// ТИПЫ
// ============================================================
export type SortDirection = "asc" | "desc" | null;
export type FilterValue = string | boolean | null;

export interface ColumnState {
  sort: SortDirection;
  filter: FilterValue;
}

export type ColumnStates = Record<string, ColumnState>;

export interface ColumnDef {
  id: string;
  label: string;
  /** Тип данных для корректного рендера фильтра */
  type: "string" | "number" | "date" | "boolean" | "select";
  /** Варианты для type: "select" */
  options?: Array<{ value: string; label: string }>;
}

interface ColumnHeaderMenuProps {
  column: ColumnDef;
  state: ColumnState;
  onChange: (columnId: string, patch: Partial<ColumnState>) => void;
}

// ============================================================
// КОМПОНЕНТ
// ============================================================
export const ColumnHeaderMenu = ({
  column,
  state,
  onChange,
}: ColumnHeaderMenuProps) => {
  const [isFilterOpen, setIsFilterOpen] = useState(false);
  const [draftFilter, setDraftFilter] = useState<FilterValue>(state.filter);

  const hasFilter = state.filter !== null && state.filter !== "";
  const hasSort = state.sort !== null;

  const applyFilter = useCallback(() => {
    onChange(column.id, { filter: draftFilter });
    setIsFilterOpen(false);
  }, [column.id, draftFilter, onChange]);

  const clearFilter = useCallback(() => {
    onChange(column.id, { filter: null });
    setDraftFilter(null);
  }, [column.id, onChange]);

  const clearSort = useCallback(() => {
    onChange(column.id, { sort: null });
  }, [column.id, onChange]);

  const setSortAsc = useCallback(() => {
    onChange(column.id, { sort: "asc" });
  }, [column.id, onChange]);

  const setSortDesc = useCallback(() => {
    onChange(column.id, { sort: "desc" });
  }, [column.id, onChange]);

  const openFilterDialog = useCallback(() => {
    setDraftFilter(state.filter);
    setIsFilterOpen(true);
  }, [state.filter]);

  // Мемоизированные иконки-индикаторы (Правило №46)
  const indicators = useMemo(() => {
    const parts: React.ReactNode[] = [];
    if (hasSort) {
      parts.push(
        state.sort === "asc" ? (
          <ArrowUp key="sort" className="inline h-3 w-3 ml-1 text-blue-600" />
        ) : (
          <ArrowDown key="sort" className="inline h-3 w-3 ml-1 text-blue-600" />
        ),
      );
    }
    if (hasFilter) {
      parts.push(
        <Filter
          key="filter"
          className="inline h-3 w-3 ml-1 text-green-600 dark:text-green-400"
        />,
      );
    }
    return parts;
  }, [hasSort, hasFilter, state.sort]);

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button
            type="button"
            className="inline-flex items-center gap-1 text-xs font-medium hover:bg-accent rounded px-1 py-0.5 transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1"
            title="Настройки колонки"
          >
            {column.label}
            {indicators}
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-56">
          {/* Сортировка */}
          {hasSort ? (
            <>
              <DropdownMenuItem onClick={clearSort}>
                <ArrowDownUp className="mr-2 h-4 w-4" />
                Отменить сортировку
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={state.sort === "asc" ? setSortDesc : setSortAsc}
              >
                {state.sort === "asc" ? (
                  <ArrowDown className="mr-2 h-4 w-4" />
                ) : (
                  <ArrowUp className="mr-2 h-4 w-4" />
                )}
                Изменить сортировку
              </DropdownMenuItem>
            </>
          ) : (
            <>
              <DropdownMenuItem onClick={setSortAsc}>
                <ArrowUp className="mr-2 h-4 w-4" />
                Сортировка по возрастанию
              </DropdownMenuItem>
              <DropdownMenuItem onClick={setSortDesc}>
                <ArrowDown className="mr-2 h-4 w-4" />
                Сортировка по убыванию
              </DropdownMenuItem>
            </>
          )}

          <DropdownMenuSeparator />

          {/* Фильтр */}
          {hasFilter ? (
            <>
              <DropdownMenuItem onClick={clearFilter}>
                <FilterX className="mr-2 h-4 w-4" />
                Отменить фильтр
              </DropdownMenuItem>
              <DropdownMenuItem onClick={openFilterDialog}>
                <Filter className="mr-2 h-4 w-4" />
                Изменить фильтр
              </DropdownMenuItem>
            </>
          ) : (
            <DropdownMenuItem onClick={openFilterDialog}>
              <Filter className="mr-2 h-4 w-4" />
              Добавить фильтр
            </DropdownMenuItem>
          )}
        </DropdownMenuContent>
      </DropdownMenu>

      {/* Модальное окно ввода фильтра */}
      <Dialog open={isFilterOpen} onOpenChange={setIsFilterOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Фильтр: {column.label}</DialogTitle>
          </DialogHeader>
          <div className="space-y-2 py-2">
            <Label htmlFor={`filter-${column.id}`}>
              Значение для фильтрации
            </Label>
            <FilterInput
              column={column}
              value={draftFilter}
              onChange={setDraftFilter}
            />
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                clearFilter();
                setIsFilterOpen(false);
              }}
            >
              Сбросить
            </Button>
            <Button onClick={applyFilter}>Применить</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
};

// ============================================================
// ДИНАМИЧЕСКИЙ INPUT ДЛЯ ФИЛЬТРА
// ============================================================
interface FilterInputProps {
  column: ColumnDef;
  value: FilterValue;
  onChange: (value: FilterValue) => void;
}

const FilterInput = ({ column, value, onChange }: FilterInputProps) => {
  const inputId = `filter-${column.id}`;

  if (column.type === "boolean") {
    return (
      <Select
        value={value === null ? "any" : String(value)}
        onValueChange={(v) =>
          onChange(v === "any" ? null : v === "true")
        }
      >
        <SelectTrigger>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="any">Любое</SelectItem>
          <SelectItem value="true">Да</SelectItem>
          <SelectItem value="false">Нет</SelectItem>
        </SelectContent>
      </Select>
    );
  }

  if (column.type === "select" && column.options) {
    return (
      <Select
        value={value === null ? "any" : String(value)}
        onValueChange={(v) => onChange(v === "any" ? null : v)}
      >
        <SelectTrigger>
          <SelectValue placeholder="Выберите..." />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="any">Любое</SelectItem>
          {column.options.map((opt) => (
            <SelectItem key={opt.value} value={opt.value}>
              {opt.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    );
  }

  if (column.type === "date") {
    return (
      <Input
        id={inputId}
        type="date"
        value={(value as string) ?? ""}
        onChange={(e) => onChange(e.target.value || null)}
      />
    );
  }

  if (column.type === "number") {
    return (
      <Input
        id={inputId}
        type="number"
        value={(value as string) ?? ""}
        onChange={(e) => onChange(e.target.value || null)}
        placeholder="Введите число..."
      />
    );
  }

  // string (по умолчанию)
  return (
    <Input
      id={inputId}
      type="text"
      value={(value as string) ?? ""}
      onChange={(e) => onChange(e.target.value || null)}
      placeholder="Введите текст..."
    />
  );
};