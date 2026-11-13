// frontend/src/lib/ui-preferences/tableColumnStates.ts
import {
  TableColumnStateSchemaSort,
//   type TableColumnStateSchema,
} from "@/api/generated/coolERP.schemas";

/** Плоские значения сортировки колонок (контракт ColumnHeaderMenu). */
export type ColumnSort = "asc" | "desc";

const SORT_TO_API: Record<ColumnSort, TableColumnStateSchemaSort> = {
  asc: TableColumnStateSchemaSort.asc,
  desc: TableColumnStateSchemaSort.desc,
};

const SORT_FROM_API: Record<TableColumnStateSchemaSort, ColumnSort> = {
  [TableColumnStateSchemaSort.asc]: "asc",
  [TableColumnStateSchemaSort.desc]: "desc",
};

/** «asc» | «desc» | null → enum Orval (строковые enum номинальны). */
export const columnSortToApi = (
  sort: ColumnSort | null,
): TableColumnStateSchemaSort | null => (sort === null ? null : SORT_TO_API[sort]);

/** enum Orval → плоское значение; null/undefined означают «сортировки нет». */
export const columnSortFromApi = (
  sort: TableColumnStateSchemaSort | null | undefined,
): ColumnSort | null => {
  if (sort === null || sort === undefined) return null;
  return SORT_FROM_API[sort];
};

/**
 * FilterValue (`string | number | boolean | null`) → строка для API и хранилища.
 * Числа сериализуются строковым представлением: числовые фильтры колонок
 * (`type: "number"`) хранят значение как number, и ранее оно терялось.
 * Пустая строка нормализуется в null; булевы фильтры не сериализуются
 * (колонок с таким типом среди персистентных таблиц нет).
 */
export const columnFilterToApi = (filter: unknown): string | null => {
  if (typeof filter === "string") return filter === "" ? null : filter;
  if (typeof filter === "number" && Number.isFinite(filter)) {
    return String(filter);
  }
  return null;
};

/** filter в схеме опционален; локальный тип колонки требует string | null. */
export const columnFilterFromApi = (
  filter: string | null | undefined,
): string | null => filter ?? null;