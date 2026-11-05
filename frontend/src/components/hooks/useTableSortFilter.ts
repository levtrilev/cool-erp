import { useState, useMemo, useCallback } from "react";
import type {
  ColumnDef,
  ColumnState,
  ColumnStates,
  FilterValue,
  SortDirection,
} from "@/core/notes/ColumnHeaderMenu";

/**
 * Хук для клиентской сортировки и фильтрации списков.
 * Правило №46: все вычисления через useMemo, без каскадных setState.
 */
export const useTableSortFilter = <T extends Record<string, unknown>>(
  items: T[],
  columns: ColumnDef[],
  /** Функция извлечения значения поля из элемента */
  getValue: (item: T, columnId: string) => string | number | boolean | null,
) => {
  const [columnStates, setColumnStates] = useState<ColumnStates>(() => {
    const initial: ColumnStates = {};
    for (const col of columns) {
      initial[col.id] = { sort: null, filter: null };
    }
    return initial;
  });

  const handleColumnChange = useCallback(
    (columnId: string, patch: Partial<ColumnState>) => {
      setColumnStates((prev) => ({
        ...prev,
        [columnId]: { ...prev[columnId], ...patch },
      }));
    },
    [],
  );

  const resetAll = useCallback(() => {
    setColumnStates(() => {
      const initial: ColumnStates = {};
      for (const col of columns) {
        initial[col.id] = { sort: null, filter: null };
      }
      return initial;
    });
  }, [columns]);

  // ✅ Правило №46: вычисляемые значения через useMemo
  const processedItems = useMemo(() => {
    // 1. Фильтрация
    let result = items.filter((item) => {
      for (const col of columns) {
        const state = columnStates[col.id];
        if (state.filter === null || state.filter === "") continue;
        const value = getValue(item, col.id);
        if (!matchFilter(value, state.filter, col.type)) {
          return false;
        }
      }
      return true;
    });

    // 2. Сортировка (находим первую колонку с сортировкой)
    const sortCol = columns.find((c) => columnStates[c.id].sort !== null);
    if (sortCol) {
      const direction = columnStates[sortCol.id].sort as SortDirection;
      result = [...result].sort((a, b) => {
        const va = getValue(a, sortCol.id);
        const vb = getValue(b, sortCol.id);
        return compareValues(va, vb, direction);
      });
    }

    return result;
  }, [items, columns, columnStates, getValue]);

  return {
    columnStates,
    handleColumnChange,
    resetAll,
    processedItems,
  };
};

// ============================================================
// ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
// ============================================================
function matchFilter(
  value: string | number | boolean | null,
  filter: FilterValue,
  type: ColumnDef["type"],
): boolean {
  if (filter === null || filter === "") return true;

  if (type === "boolean") {
    return value === filter;
  }

  if (type === "select") {
    return String(value) === String(filter);
  }

  if (type === "date") {
    if (!value) return false;
    // Сравнение дат: filter = "YYYY-MM-DD", value может быть ISO-строка
    const valDate = new Date(value as string).toISOString().slice(0, 10);
    return valDate === String(filter);
  }

  if (type === "number") {
    const numVal = Number(value);
    const numFilter = Number(filter);
    if (Number.isNaN(numVal) || Number.isNaN(numFilter)) return false;
    return numVal === numFilter;
  }

  // string: частичное совпадение без учёта регистра
  if (value === null || value === undefined) return false;
  return String(value).toLowerCase().includes(String(filter).toLowerCase());
}

function compareValues(
  a: string | number | boolean | null,
  b: string | number | boolean | null,
  direction: SortDirection,
): number {
  if (a === null && b === null) return 0;
  if (a === null) return 1;
  if (b === null) return -1;

  let result = 0;
  if (typeof a === "number" && typeof b === "number") {
    result = a - b;
  } else if (typeof a === "boolean" && typeof b === "boolean") {
    result = Number(a) - Number(b);
  } else {
    result = String(a).localeCompare(String(b), "ru", { numeric: true });
  }

  return direction === "desc" ? -result : result;
}