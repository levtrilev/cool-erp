// frontend/src/modules/sales/orders/OrdersPage.tsx
import {
  useState,
  useEffect,
  useCallback,
  useMemo,
  type Dispatch,
  type SetStateAction,
} from "react";
import { keepPreviousData, useQueryClient } from "@tanstack/react-query";
import {
  Plus,
  Trash2,
  Search,
  Loader2,
  Lock,
  Copy,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/components/ui/use-toast";
import {
  useGetSalesOrdersSalesOrdersGet,
  useDeleteSalesOrderSalesOrdersOrderIdDelete,
  getSalesOrdersSalesOrdersGet,
  useAcquireSalesOrderLockSalesOrdersOrderIdLockPost,
  useReleaseSalesOrderLockSalesOrdersOrderIdLockDelete,
} from "@/api/generated/sales-orders/sales-orders";
import { EditSalesOrderModal } from "@/modules/sales/orders/EditSalesOrderModal";
import { useResizableColumns } from "@/components/hooks/useResizableColumns";
import { DOC_STATUS_LABELS } from "./schemas";
import {
  ColumnHeaderMenu,
  type ColumnDef,
  type ColumnState,
  type ColumnStates,
} from "@/core/notes/ColumnHeaderMenu";
import { useTablePreferences } from "@/lib/ui-preferences/useTablePreferences";
// import type {
//   UiTableColumnState,
//   UiTablePreference,
// } from "@/lib/ui-preferences/types";
import {
  SalesOrderResponseSchema,
  SalesOrderSortField,
  SortOrder,
  type TableColumnStateSchema,
  type TablePreferenceSchema,
  type TablePreferenceSchemaColumnStates,
} from "@/api/generated/coolERP.schemas";
import {
  columnFilterFromApi,
  columnFilterToApi,
  columnSortFromApi,
  columnSortToApi,
} from "@/lib/ui-preferences/tableColumnStates";

const toStoredOrders = (
  state: OrdersTableViewState,
): TablePreferenceSchema => ({
  column_states: Object.fromEntries(
    Object.entries(state.columnStates).map(([key, value]) => [
      key,
      {
        sort: columnSortToApi(value.sort),
        filter: columnFilterToApi(value.filter),
      },
    ]),
  ),
  search: state.search,
  page: state.page,
  page_size: 15,
});

const fromStoredOrders = (
  stored: TablePreferenceSchema | undefined,
  defaults: OrdersTableViewState,
): OrdersTableViewState => {
  if (stored === undefined) return defaults;

  const columnStates: ColumnStates = buildInitialColumnStates();
  const storedColumns: TablePreferenceSchemaColumnStates =
    stored.column_states ?? {};

  for (const column of SORT_FILTER_COLUMNS) {
    const raw: TableColumnStateSchema | undefined = storedColumns[column.id];
    if (raw === undefined) continue;
    columnStates[column.id] = {
      sort: columnSortFromApi(raw.sort),
      filter: columnFilterFromApi(raw.filter),
    };
  }

  return {
    columnStates,
    search: stored.search ?? "",
    searchInput: stored.search ?? "",
    page: stored.page ?? 1,
  };
};

const SORT_FIELD_BY_COLUMN: Record<string, SalesOrderSortField> = {
  doc_number: SalesOrderSortField.doc_number,
  doc_date: SalesOrderSortField.doc_date,
  customer_name: SalesOrderSortField.customer_name,
  supplier_name: SalesOrderSortField.supplier_name,
  doc_status: SalesOrderSortField.doc_status,
  total_amount: SalesOrderSortField.total_amount,
  updated_at: SalesOrderSortField.updated_at,
};

const SORT_FILTER_COLUMNS: ColumnDef[] = [
  { id: SalesOrderSortField.doc_number, label: "Номер", type: "string" },
  { id: SalesOrderSortField.doc_date, label: "Дата", type: "date" },
  { id: SalesOrderSortField.customer_name, label: "Заказчик", type: "string" },
  { id: SalesOrderSortField.supplier_name, label: "Поставщик", type: "string" },
  {
    id: SalesOrderSortField.doc_status,
    label: "Статус",
    type: "select",
    options: Object.entries(DOC_STATUS_LABELS).map(([value, label]) => ({
      value,
      label,
    })),
  },
  { id: SalesOrderSortField.total_amount, label: "Сумма", type: "number" },
  { id: SalesOrderSortField.updated_at, label: "Обновлено", type: "date" },
];

const COLUMNS = [
  { id: "doc_number", initialWidth: 120, minWidth: 80 },
  { id: "doc_date", initialWidth: 120, minWidth: 80 },
  { id: "customer_name", initialWidth: 200, minWidth: 120 },
  { id: "supplier_name", initialWidth: 200, minWidth: 120 },
  { id: "doc_status", initialWidth: 130, minWidth: 100 },
  { id: "total_amount", initialWidth: 120, minWidth: 80 },
  { id: "updated_at", initialWidth: 160, minWidth: 120 },
  { id: "actions", initialWidth: 100, minWidth: 80 },
];

const buildInitialColumnStates = (): ColumnStates =>
  Object.fromEntries(
    SORT_FILTER_COLUMNS.map((c) => [c.id, { sort: null, filter: null }]),
  );

/** Параметры выборки без пагинации — тип выводится из Orval-функции. */
type OrdersQueryFilters = Omit<
  NonNullable<Parameters<typeof getSalesOrdersSalesOrdersGet>[0]>,
  "skip" | "limit"
>;

// ── Персистентное состояние вида таблицы (серверное) ──────────────
interface OrdersTableViewState {
  columnStates: ColumnStates;
  search: string;
  searchInput: string;
  page: number;
}

const ORDERS_TABLE_DEFAULT_STATE: OrdersTableViewState = {
  columnStates: buildInitialColumnStates(),
  search: "",
  searchInput: "",
  page: 1,
};

// const toStoredOrders = (
//   state: OrdersTableViewState,
// ): TablePreferenceSchema => ({
//   column_states: Object.fromEntries(
//     Object.entries(state.columnStates).map(([key, value]) => [
//       key,
//       { sort: value.sort, filter: value.filter },
//     ]),
//   ),
//   search: state.search,
//   page: state.page,
//   page_size: 15,
// });

// const fromStoredOrders = (
//   stored: UiTablePreference | undefined,
//   defaults: OrdersTableViewState,
// ): OrdersTableViewState => {
//   if (stored === undefined) return defaults;
//   const columnStates: ColumnStates = buildInitialColumnStates();
//   for (const column of SORT_FILTER_COLUMNS) {
//     const raw: UiTableColumnState | undefined = stored.column_states[column.id];
//     if (raw) {
//       columnStates[column.id] = { sort: raw.sort, filter: raw.filter };
//     }
//   }
//   return {
//     columnStates,
//     search: stored.search,
//     searchInput: stored.search,
//     page: stored.page,
//   };
// };

export const OrdersPage = () => {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  // ✅ Персистентный вид таблицы: сортировка, фильтры колонок, поиск, страница.
  // Восстанавливается между переходами, сессиями и устройствами.
  const {
    state: viewState,
    setState: setViewState,
    isRestored,
  } = useTablePreferences<OrdersTableViewState>({
    tableKey: "sales-orders",
    defaultState: ORDERS_TABLE_DEFAULT_STATE,
    toStored: toStoredOrders,
    fromStored: fromStoredOrders,
  });

  const columnStates: ColumnStates = viewState.columnStates;
  const search: string = viewState.search;
  const searchInput: string = viewState.searchInput;
  const page: number = viewState.page;
  const [limit] = useState(15);

  // Обёртки сохраняют прежние имена сеттеров — остальной код не меняется.
  const setPage = useCallback(
    (next: number): void => {
      setViewState((prev) => ({ ...prev, page: next }));
    },
    [setViewState],
  );

  const setSearch = useCallback(
    (next: string): void => {
      setViewState((prev) => ({ ...prev, search: next }));
    },
    [setViewState],
  );

  const setSearchInput = useCallback(
    (next: string): void => {
      setViewState((prev) => ({ ...prev, searchInput: next }));
    },
    [setViewState],
  );

  const setColumnStates = useCallback<Dispatch<SetStateAction<ColumnStates>>>(
    (action) => {
      setViewState((prev) => ({
        ...prev,
        columnStates:
          typeof action === "function" ? action(prev.columnStates) : action,
      }));
    },
    [setViewState],
  );

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingOrder, setEditingOrder] =
    useState<SalesOrderResponseSchema | null>(null);
  const [deleteOrderId, setDeleteOrderId] = useState<string | null>(null);
  const [highlightedOrderId, setHighlightedOrderId] = useState<string | null>(
    null,
  );
  const [readOnly, setReadOnly] = useState(false);
  const [readOnlyReason, setReadOnlyReason] = useState<string>("");
  const [copyingOrder, setCopyingOrder] =
    useState<SalesOrderResponseSchema | null>(null);
  const [isCopyOpen, setIsCopyOpen] = useState(false);

  const { widths, handleMouseDown, resetWidths } = useResizableColumns(
    COLUMNS,
    "orders-table-widths",
  );

  // ✅ Производные значения через useMemo (Правило №46)
  const sortColumnId = useMemo(
    () =>
      Object.keys(columnStates).find((id) => columnStates[id].sort !== null) ??
      null,
    [columnStates],
  );

  const sortDirection = sortColumnId ? columnStates[sortColumnId].sort : null;

  const strFilter = useCallback(
    (columnId: string): string | undefined => {
      const value = columnStates[columnId]?.filter;
      return typeof value === "string" && value.length > 0 ? value : undefined;
    },
    [columnStates],
  );
  // ✅ Числовые фильтры: меню хранит значение как number ИЛИ string —
  // приводим оба варианта к строке-транспорту для API и персистенции.
  const numberFilter = useCallback(
    (columnId: string): string | undefined => {
      const value = columnStates[columnId]?.filter;
      if (typeof value === "number" && Number.isFinite(value)) {
        return String(value);
      }
      if (typeof value === "string" && value.trim().length > 0) {
        return value.trim();
      }
      return undefined;
    },
    [columnStates],
  );
  const hasActiveFiltersOrSort = useMemo(
    () =>
      sortColumnId !== null ||
      Object.values(columnStates).some(
        (s) => s.filter !== null && s.filter !== "",
      ),
    [columnStates, sortColumnId],
  );

  // ✅ Единый набор условий выборки: используется списком и поиском позиции
  // записи после сохранения, поэтому номер страницы считается по тому же
  // порядку, который видит пользователь.
  const queryFilters: OrdersQueryFilters = useMemo(
    () => ({
      search: search || undefined,
      sort_by: sortColumnId ? SORT_FIELD_BY_COLUMN[sortColumnId] : undefined,
      sort_order: sortColumnId
        ? sortDirection === "desc"
          ? SortOrder.desc
          : SortOrder.asc
        : undefined,
      filter_doc_number: strFilter("doc_number"),
      filter_doc_date: strFilter("doc_date"),
      filter_customer_name: strFilter("customer_name"),
      filter_supplier_name: strFilter("supplier_name"),
      filter_doc_status: strFilter("doc_status"),
      filter_updated_at: strFilter("updated_at"),
      filter_total_amount: numberFilter("total_amount"),
    }),
    [search, sortColumnId, sortDirection, strFilter, numberFilter],
  );

  const { data, isLoading, refetch } = useGetSalesOrdersSalesOrdersGet(
    {
      skip: (page - 1) * limit,
      limit,
      ...queryFilters,
    },
    {
      query: {
        enabled: isRestored,
        placeholderData: keepPreviousData,
      },
    },
  );

  const deleteMutation = useDeleteSalesOrderSalesOrdersOrderIdDelete();
  const acquireLockMutation =
    useAcquireSalesOrderLockSalesOrdersOrderIdLockPost();
  const releaseLockMutation =
    useReleaseSalesOrderLockSalesOrdersOrderIdLockDelete();

  // ✅ Правило №46, п. 2.3: стабильная ссылка на список для зависимостей.
  const pageMeta = data?.data;
  const items: SalesOrderResponseSchema[] = useMemo(
    () => pageMeta?.items ?? [],
    [pageMeta?.items],
  );
  const total: number = pageMeta?.total ?? 0;
  const totalPages: number = Math.max(1, Math.ceil(total / limit));

  // Защита от выхода за границы: сохранённый номер страницы может оказаться
  // больше последней существующей после удалений или смены фильтров.
  useEffect(() => {
    if (!isRestored || data === undefined) return;
    if (page > totalPages) setPage(totalPages);
  }, [isRestored, data, page, totalPages, setPage]);

  // ✅ Обработчик меню колонки: одна сортировка на таблицу + сброс страницы
  const handleColumnChange = useCallback(
    (columnId: string, patch: Partial<ColumnState>) => {
      setColumnStates((prev) => {
        const next: ColumnStates = {
          ...prev,
          [columnId]: { ...prev[columnId], ...patch },
        };
        if (patch.sort !== undefined && patch.sort !== null) {
          for (const key of Object.keys(next)) {
            if (key !== columnId) {
              next[key] = { ...next[key], sort: null };
            }
          }
        }
        return next;
      });
      setPage(1);
    },
    [setColumnStates, setPage],
  );

  const resetFiltersAndSort = useCallback(() => {
    setColumnStates(buildInitialColumnStates());
    setPage(1);
  }, [setColumnStates, setPage]);

  // ✅ Правило №18 и №23: умная навигация и подсветка.
  // Состав страницы берётся из результата refetch, а не из data в замыкании;
  // позиция ищется с теми же sort/фильтрами, что и видимый список.
  const handleSaved = useCallback(
    async (id: string, docNumber?: string): Promise<void> => {
      await queryClient.invalidateQueries({ queryKey: ["sales-orders"] });
      const refreshed = await refetch();
      const currentItems: SalesOrderResponseSchema[] =
        refreshed.data?.data?.items ?? [];

      if (currentItems.some((item) => item.id === id)) {
        setHighlightedOrderId(id);
        toast({ title: "Успешно сохранено" });
        return;
      }

      try {
        const fullList = await getSalesOrdersSalesOrdersGet({
          limit: 1000,
          skip: 0,
          ...queryFilters,
        });
        const foundIndex: number = (fullList.data?.items ?? []).findIndex(
          (item) => item.id === id,
        );
        if (foundIndex === -1) {
          toast({
            title: "Сохранено",
            description:
              "Запись не отображается в текущем списке: она не подходит под активные фильтры или условия поиска.",
          });
          return;
        }

        const targetPage: number = Math.floor(foundIndex / limit) + 1;
        toast({
          title: "Сохранено",
          description: `Запись «${docNumber ?? ""}» теперь на странице ${targetPage}.`,
          action: (
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setPage(targetPage);
                setHighlightedOrderId(id);
              }}
            >
              Перейти
            </Button>
          ),
        });
      } catch (error: unknown) {
        const err = error as { response?: { data?: { detail?: string } } };
        toast({
          variant: "destructive",
          title: "Ошибка навигации",
          description:
            err?.response?.data?.detail || "Не удалось определить страницу",
        });
      }
    },
    [queryClient, refetch, queryFilters, limit, setPage, toast],
  );

  // ✅ Правило №25: refetch после удаления + безопасная обработка ошибок
  const handleDelete = async (): Promise<void> => {
    if (!deleteOrderId) return;
    try {
      await deleteMutation.mutateAsync({ orderId: deleteOrderId });
      await refetch();
      setDeleteOrderId(null);
      toast({ title: "Заказ удалён" });
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      toast({
        variant: "destructive",
        title: "Ошибка удаления",
        description: err?.response?.data?.detail || "Не удалось удалить",
      });
    }
  };

  const openEdit = async (item: SalesOrderResponseSchema): Promise<void> => {
    setEditingOrder(item);
    if (item.is_editing_locked) {
      setReadOnly(true);
      setReadOnlyReason(
        "Документ редактируется другим пользователем. Вы можете только просматривать данные.",
      );
      setIsModalOpen(true);
      return;
    }
    try {
      await acquireLockMutation.mutateAsync({ orderId: item.id });
      setReadOnly(false);
      setReadOnlyReason("");
      setIsModalOpen(true);
    } catch (error: unknown) {
      const err = error as {
        response?: { status?: number; data?: { detail?: string } };
      };
      const status = err?.response?.status;
      if (status === 403) {
        setReadOnly(true);
        setReadOnlyReason(
          "У вас нет прав на изменение этого документа. Доступен только просмотр.",
        );
        setIsModalOpen(true);
      } else if (status === 423) {
        setReadOnly(true);
        setReadOnlyReason(
          "Документ редактируется другим пользователем. Открыт в режиме только для чтения.",
        );
        setIsModalOpen(true);
        toast({
          variant: "destructive",
          title: "Документ занят",
          description: "Документ редактируется другим пользователем.",
        });
      } else {
        toast({
          variant: "destructive",
          title: "Ошибка блокировки",
          description:
            err?.response?.data?.detail || "Не удалось открыть документ",
        });
      }
    }
  };

  const openCopy = (item: SalesOrderResponseSchema): void => {
    setCopyingOrder(item);
    setIsCopyOpen(true);
  };

  const handleCopyModalOpenChange = (open: boolean): void => {
    setIsCopyOpen(open);
    if (!open) setCopyingOrder(null);
  };

  const handleModalClose = async (open: boolean): Promise<void> => {
    if (!open && editingOrder && !readOnly) {
      try {
        await releaseLockMutation.mutateAsync({ orderId: editingOrder.id });
      } catch {
        // Игнорируем ошибки освобождения
      }
    }
    setIsModalOpen(open);
    if (!open) {
      setEditingOrder(null);
      setReadOnly(false);
      setReadOnlyReason("");
    }
  };

  // ✅ Правило №17: единственный таймер подсветки с автосбросом
  useEffect(() => {
    if (
      highlightedOrderId &&
      items.some((item) => item.id === highlightedOrderId)
    ) {
      const timer = setTimeout(() => setHighlightedOrderId(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [items, highlightedOrderId]);

  const openCreate = (): void => {
    setEditingOrder(null);
    setReadOnly(false);
    setIsModalOpen(true);
  };

  const formatDate = (iso: string | null | undefined): string => {
    if (!iso) return "—";
    return new Date(iso).toLocaleString("ru-RU", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const formatDocDate = (iso: string | null | undefined): string => {
    if (!iso) return "—";
    return new Date(iso).toLocaleDateString("ru-RU");
  };

  const renderSortableHeader = (columnId: string) => {
    const col = SORT_FILTER_COLUMNS.find((c) => c.id === columnId);
    if (!col) return null;
    return (
      <TableHead
        style={{ width: widths[columnId as keyof typeof widths] }}
        className="relative"
      >
        <ColumnHeaderMenu
          column={col}
          state={columnStates[columnId]}
          onChange={handleColumnChange}
        />
        <div
          className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary/20"
          onMouseDown={(e) => handleMouseDown(columnId, e)}
        />
      </TableHead>
    );
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Заказы продаж</h1>
          <p className="text-xs text-muted-foreground mt-0.5 tabular-nums">
            Всего: {total}
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={resetWidths}>
            Сбросить ширину
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={resetFiltersAndSort}
            disabled={!hasActiveFiltersOrSort}
          >
            Сбросить фильтры/сортировку
          </Button>
          <Button onClick={openCreate}>
            <Plus className="h-4 w-4 mr-2" /> Создать заказ
          </Button>
        </div>
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          setSearch(searchInput);
          setPage(1);
        }}
        className="flex gap-2"
      >
        <Input
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          placeholder="Поиск по номеру и контакту..."
          className="max-w-md"
        />
        <Button type="submit">
          <Search className="h-4 w-4 mr-2" /> Найти
        </Button>
      </form>

      {!isRestored || isLoading ? (
        <div className="flex items-center justify-center h-40">
          <Loader2 className="h-6 w-6 animate-spin" />
        </div>
      ) : (
        <div className="rounded-md border overflow-auto max-h-[calc(100vh-260px)]">
          <Table className="table-fixed w-full">
            <TableHeader className="sticky top-0 bg-background z-10 shadow-sm">
              <TableRow className="h-10 hover:bg-transparent">
                {renderSortableHeader("doc_number")}
                {renderSortableHeader("doc_date")}
                {renderSortableHeader("customer_name")}
                {renderSortableHeader("supplier_name")}
                {renderSortableHeader("doc_status")}
                {renderSortableHeader("total_amount")}
                {renderSortableHeader("updated_at")}
                <TableHead
                  style={{ width: widths.actions }}
                  className="relative"
                >
                  Действия
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.length === 0 ? (
                <TableRow>
                  <TableCell
                    colSpan={8}
                    className="text-center py-8 text-muted-foreground"
                  >
                    {hasActiveFiltersOrSort || search
                      ? "Нет записей, соответствующих условиям"
                      : "Заказы не найдены"}
                  </TableCell>
                </TableRow>
              ) : (
                items.map((item) => (
                  <TableRow
                    key={item.id}
                    className={
                      highlightedOrderId === item.id
                        ? "bg-yellow-100 dark:bg-yellow-900/30 transition-colors duration-300"
                        : ""
                    }
                  >
                    <TableCell
                      style={{ width: widths.doc_number }}
                      className="py-1 align-top overflow-hidden"
                    >
                      <button
                        type="button"
                        onClick={() => openEdit(item)}
                        className="text-left text-link hover:text-link-hover hover:underline underline-offset-2 font-medium cursor-pointer w-full truncate block focus:outline-none focus:ring-2 focus:ring-link focus:ring-offset-1 rounded-sm transition-colors"
                        title={item.doc_number ?? "Без номера"}
                      >
                        {item.is_editing_locked && (
                          <Lock className="inline h-3 w-3 mr-1 text-amber-500" />
                        )}
                        {item.doc_number ?? "Без номера"}
                      </button>
                    </TableCell>
                    <TableCell
                      style={{ width: widths.doc_date }}
                      className="py-1 align-top"
                    >
                      {formatDocDate(item.doc_date)}
                    </TableCell>
                    <TableCell
                      style={{ width: widths.customer_name }}
                      className="py-1 align-top overflow-hidden"
                    >
                      <div className="truncate">
                        {(
                          item as SalesOrderResponseSchema & {
                            customer_name?: string;
                          }
                        ).customer_name ?? "—"}
                      </div>
                    </TableCell>
                    <TableCell
                      style={{ width: widths.supplier_name }}
                      className="py-1 align-top overflow-hidden"
                    >
                      <div className="truncate">
                        {(
                          item as SalesOrderResponseSchema & {
                            supplier_name?: string;
                          }
                        ).supplier_name ?? "—"}
                      </div>
                    </TableCell>
                    <TableCell
                      style={{ width: widths.doc_status }}
                      className="py-1 align-top"
                    >
                      <Badge variant="secondary">
                        {DOC_STATUS_LABELS[item.doc_status] ?? item.doc_status}
                      </Badge>
                    </TableCell>
                    <TableCell
                      style={{ width: widths.total_amount }}
                      className="py-1 align-top text-right"
                    >
                      {Number(item.total_amount).toFixed(2)}
                    </TableCell>
                    <TableCell
                      style={{ width: widths.updated_at }}
                      className="py-1 align-top text-xs text-muted-foreground"
                    >
                      {formatDate(item.updated_at)}
                    </TableCell>
                    <TableCell
                      style={{ width: widths.actions }}
                      className="py-1 align-top"
                    >
                      <div className="flex gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7"
                          onClick={() => openCopy(item)}
                          title="Копировать"
                        >
                          <Copy className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7 text-destructive hover:text-destructive"
                          onClick={() => setDeleteOrderId(item.id)}
                          title="Удалить"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      )}

      {/* ✅ Пагинация по образцу AdminRolesPage (Правило №15) */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-1 mt-3">
          <Button
            size="sm"
            variant="outline"
            className="h-8 w-8 p-0"
            disabled={page === 1}
            onClick={() => setPage(1)}
            aria-label="Первая страница"
          >
            <ChevronsLeft className="h-4 w-4" />
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="h-8 w-8 p-0"
            disabled={page === 1}
            onClick={() => setPage(page - 1)}
            aria-label="Предыдущая страница"
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
            let pageNum = i + 1;
            if (totalPages > 5 && page > 3) pageNum = page - 2 + i;
            if (pageNum > totalPages) return null;
            return (
              <Button
                key={pageNum}
                size="sm"
                variant={page === pageNum ? "default" : "outline"}
                className="h-8 w-8 p-0 tabular-nums"
                onClick={() => setPage(pageNum)}
                aria-current={page === pageNum ? "page" : undefined}
              >
                {pageNum}
              </Button>
            );
          })}
          <Button
            size="sm"
            variant="outline"
            className="h-8 w-8 p-0"
            disabled={page === totalPages}
            onClick={() => setPage(page + 1)}
            aria-label="Следующая страница"
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="h-8 w-8 p-0"
            disabled={page === totalPages}
            onClick={() => setPage(totalPages)}
            aria-label="Последняя страница"
          >
            <ChevronsRight className="h-4 w-4" />
          </Button>
        </div>
      )}

      <EditSalesOrderModal
        open={isModalOpen}
        onOpenChange={handleModalClose}
        initialData={editingOrder}
        onSaved={handleSaved}
        readOnly={readOnly}
        readOnlyReason={readOnlyReason}
      />

      {isCopyOpen && copyingOrder && (
        <EditSalesOrderModal
          key={`copy-${copyingOrder.id}`}
          open={isCopyOpen}
          onOpenChange={handleCopyModalOpenChange}
          initialData={null}
          copyFromOrder={copyingOrder}
          onSaved={handleSaved}
        />
      )}

      <AlertDialog
        open={!!deleteOrderId}
        onOpenChange={(open) => !open && setDeleteOrderId(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Удалить заказ?</AlertDialogTitle>
            <AlertDialogDescription>
              Заказ будет помечен как удалённый (мягкое удаление). Запись
              останется в БД для аудита, но перестанет отображаться в списках.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Отмена</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              disabled={deleteMutation.isPending}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleteMutation.isPending ? (
                <Loader2 className="animate-spin mr-2 h-4 w-4" />
              ) : (
                <Trash2 className="mr-2 h-4 w-4" />
              )}
              Удалить
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};
