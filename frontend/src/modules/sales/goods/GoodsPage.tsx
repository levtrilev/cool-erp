// frontend/src/modules/sales/goods/GoodsPage.tsx (полная замена)
import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import { useQueryClient, keepPreviousData } from "@tanstack/react-query";
import {
  Plus,
  Trash2,
  Search,
  Loader2,
  Lock,
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
import { useToast } from "@/components/ui/use-toast";
import {
  useListGoodsSalesGoodsGet,
  useDeleteGoodsSalesGoodsGoodsIdDelete,
  listGoodsSalesGoodsGet,
  useAcquireGoodsLockSalesGoodsGoodsIdLockPost,
  useReleaseGoodsLockSalesGoodsGoodsIdLockDelete,
} from "@/api/generated/sales-goods/sales-goods";
import {
  SalesGoodsResponseSchema,
  SalesGoodsSortField,
  SortOrder,
  type TableColumnStateSchema,
  type TablePreferenceSchema,
  type TablePreferenceSchemaColumnStates,
} from "@/api/generated/coolERP.schemas";
import { EditGoodModal } from "./EditGoodModal";
import { useResizableColumns } from "@/components/hooks/useResizableColumns";
import {
  ColumnHeaderMenu,
  type ColumnDef,
  type ColumnState,
  type ColumnStates,
} from "@/core/notes/ColumnHeaderMenu";
import { useTablePreferences } from "@/lib/ui-preferences/useTablePreferences";
import {
  columnFilterFromApi,
  columnFilterToApi,
  columnSortFromApi,
  columnSortToApi,
} from "@/lib/ui-preferences/tableColumnStates";

/**
 * ✅ P3: колонка «Раздел» скрыта ТОЛЬКО из представления.
 * Определение колонки, ширина и JSX оставлены в коде под этим флагом:
 * возврат в таблицу = переключение флага на true без иных правок.
 * Конфигурируемый набор колонок в UI — отдельная задача (не реализуется).
 */
const SHOW_SECTION_COLUMN = false;

type GoodsListParams = NonNullable<
  Parameters<typeof listGoodsSalesGoodsGet>[0]
>;
type GoodsQueryFilters = Omit<GoodsListParams, "skip" | "limit">;

const SORT_FIELD_BY_COLUMN: Record<string, SalesGoodsSortField> = {
  name: SalesGoodsSortField.name,
  item_type_name: SalesGoodsSortField.item_type_name,
  updated_at: SalesGoodsSortField.updated_at,
};

const SORT_FILTER_COLUMNS: ColumnDef[] = [
  { id: SalesGoodsSortField.name, label: "Название", type: "string" },
  { id: SalesGoodsSortField.item_type_name, label: "Тип номенклатуры", type: "string" },
  { id: SalesGoodsSortField.updated_at, label: "Обновлено", type: "date" },
];

// ✅ section_name оставлен в конфигурации ширин: возврат колонки не трогает ресайз
const COLUMNS = [
  { id: "name", initialWidth: 200, minWidth: 140 },
  { id: "item_type_name", initialWidth: 170, minWidth: 110 },
  { id: "description", initialWidth: 200, minWidth: 100 },
  { id: "author_name", initialWidth: 150, minWidth: 100 },
  { id: "section_name", initialWidth: 160, minWidth: 100 },
  { id: "updated_at", initialWidth: 150, minWidth: 110 },
  { id: "actions", initialWidth: 70, minWidth: 60 },
];

const buildInitialColumnStates = (): ColumnStates =>
  Object.fromEntries(
    SORT_FILTER_COLUMNS.map((c) => [c.id, { sort: null, filter: null }]),
  );

// ── Персистентный вид таблицы (серверный) ─────────────────────────
interface GoodsTableViewState {
  columnStates: ColumnStates;
  search: string;
  page: number;
}

const GOODS_TABLE_DEFAULT_STATE: GoodsTableViewState = {
  columnStates: buildInitialColumnStates(),
  search: "",
  page: 1,
};

const toStoredGoods = (state: GoodsTableViewState): TablePreferenceSchema => ({
  column_states: Object.fromEntries(
    Object.entries(state.columnStates).map(([key, value]) => [
      key,
      { sort: columnSortToApi(value.sort), filter: columnFilterToApi(value.filter) },
    ]),
  ),
  search: state.search,
  page: state.page,
  page_size: 10,
});

const fromStoredGoods = (
  stored: TablePreferenceSchema | undefined,
  defaults: GoodsTableViewState,
): GoodsTableViewState => {
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
    page: stored.page ?? 1,
  };
};

export const GoodsPage = () => {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const {
    state: viewState,
    setState: setViewState,
    isRestored,
  } = useTablePreferences<GoodsTableViewState>({
    tableKey: "sales-goods",
    defaultState: GOODS_TABLE_DEFAULT_STATE,
    toStored: toStoredGoods,
    fromStored: fromStoredGoods,
  });

  const columnStates: ColumnStates = viewState.columnStates;
  const search: string = viewState.search;
  const page: number = viewState.page;
  const [limit] = useState(10);

  // ✅ Правило №47: ввод поиска — локальное транзиентное состояние
  const [searchInput, setSearchInput] = useState<string>("");
  const searchInputInitializedRef = useRef<boolean>(false);

  useEffect(() => {
    if (!isRestored || searchInputInitializedRef.current) return;
    searchInputInitializedRef.current = true;
    setSearchInput(search);
  }, [isRestored, search]);

  const setPage = useCallback(
    (next: number): void => setViewState((prev) => ({ ...prev, page: next })),
    [setViewState],
  );
  const setSearch = useCallback(
    (next: string): void => setViewState((prev) => ({ ...prev, search: next })),
    [setViewState],
  );
  const setColumnStates = useCallback<
    (action: ColumnStates | ((prev: ColumnStates) => ColumnStates)) => void
  >(
    (action) =>
      setViewState((prev) => ({
        ...prev,
        columnStates:
          typeof action === "function" ? action(prev.columnStates) : action,
      })),
    [setViewState],
  );

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingGood, setEditingGood] =
    useState<SalesGoodsResponseSchema | null>(null);
  const [deleteGoodId, setDeleteGoodId] = useState<string | null>(null);
  const [highlightedGoodId, setHighlightedGoodId] = useState<string | null>(
    null,
  );
  const [readOnly, setReadOnly] = useState(false);
  const [readOnlyReason, setReadOnlyReason] = useState<string>("");

  const { widths, handleMouseDown, resetWidths } = useResizableColumns(
    COLUMNS,
    "goods-table-widths",
  );

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

  const hasActiveFiltersOrSort = useMemo(
    () =>
      sortColumnId !== null ||
      Object.values(columnStates).some(
        (s) => s.filter !== null && s.filter !== "",
      ),
    [columnStates, sortColumnId],
  );

  const queryFilters: GoodsQueryFilters = useMemo(
    () => ({
      search: search || undefined,
      sort_by: sortColumnId ? SORT_FIELD_BY_COLUMN[sortColumnId] : undefined,
      sort_order: sortColumnId
        ? sortDirection === "desc"
          ? SortOrder.desc
          : SortOrder.asc
        : undefined,
      filter_name: strFilter("name"),
      filter_item_type_name: strFilter("item_type_name"),
      filter_updated_at: strFilter("updated_at"),
    }),
    [search, sortColumnId, sortDirection, strFilter],
  );

  const { data, isLoading, refetch } = useListGoodsSalesGoodsGet(
    { skip: (page - 1) * limit, limit, ...queryFilters },
    { query: { enabled: isRestored, placeholderData: keepPreviousData } },
  );

  const deleteMutation = useDeleteGoodsSalesGoodsGoodsIdDelete();
  const acquireLockMutation = useAcquireGoodsLockSalesGoodsGoodsIdLockPost();
  const releaseLockMutation = useReleaseGoodsLockSalesGoodsGoodsIdLockDelete();

  const pageMeta = data?.data;
  const items: SalesGoodsResponseSchema[] = useMemo(
    () => pageMeta?.items ?? [],
    [pageMeta?.items],
  );
  const total: number = pageMeta?.total ?? 0;
  const totalPages: number = Math.max(1, Math.ceil(total / limit));

  useEffect(() => {
    if (!isRestored || data === undefined) return;
    if (page > totalPages) setPage(totalPages);
  }, [isRestored, data, page, totalPages, setPage]);

  const handleColumnChange = useCallback(
    (columnId: string, patch: Partial<ColumnState>) => {
      setColumnStates((prev) => {
        const next: ColumnStates = {
          ...prev,
          [columnId]: { ...prev[columnId], ...patch },
        };
        if (patch.sort !== undefined && patch.sort !== null) {
          for (const key of Object.keys(next)) {
            if (key !== columnId) next[key] = { ...next[key], sort: null };
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

  const handleGoodSaved = useCallback(
    async (id: string, name?: string): Promise<void> => {
      await queryClient.invalidateQueries({ queryKey: ["sales-goods"] });
      const refreshed = await refetch();
      const currentItems: SalesGoodsResponseSchema[] =
        refreshed.data?.data?.items ?? [];
      if (currentItems.some((item) => item.id === id)) {
        setHighlightedGoodId(id);
        toast({ title: "Успешно сохранено" });
        return;
      }
      try {
        const fullList = await listGoodsSalesGoodsGet({
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
            description: hasActiveFiltersOrSort
              ? "Запись не отображается в текущем списке: она не подходит под активные фильтры или условия поиска."
              : "Запись не найдена в списке. Обновите страницу.",
          });
          return;
        }
        const targetPage: number = Math.floor(foundIndex / limit) + 1;
        toast({
          title: "Сохранено",
          description: `Товар «${name ?? ""}» теперь на странице ${targetPage}.`,
          action: (
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setPage(targetPage);
                setHighlightedGoodId(id);
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
    [
      queryClient,
      refetch,
      queryFilters,
      limit,
      setPage,
      toast,
      hasActiveFiltersOrSort,
    ],
  );

  const handleDelete = async (): Promise<void> => {
    if (!deleteGoodId) return;
    try {
      await deleteMutation.mutateAsync({ goodsId: deleteGoodId });
      await refetch();
      setDeleteGoodId(null);
      toast({ title: "Товар удалён" });
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      toast({
        variant: "destructive",
        title: "Ошибка удаления",
        description: err?.response?.data?.detail || "Не удалось удалить товар!",
      });
    }
  };

  const openEdit = async (item: SalesGoodsResponseSchema): Promise<void> => {
    setEditingGood(item);
    if (item.is_editing_locked) {
      setReadOnly(true);
      setReadOnlyReason(
        "Документ редактируется другим пользователем. Вы можете только просматривать данные.",
      );
      setIsModalOpen(true);
      return;
    }
    try {
      await acquireLockMutation.mutateAsync({ goodsId: item.id });
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
          description: err?.response?.data?.detail || "Не удалось открыть документ",
        });
      }
    }
  };

  const handleModalClose = async (open: boolean): Promise<void> => {
    if (!open && editingGood && !readOnly) {
      try {
        await releaseLockMutation.mutateAsync({ goodsId: editingGood.id });
      } catch {
        // Ошибки освобождения игнорируются (таймаут 30 минут снимет блокировку)
      }
    }
    setIsModalOpen(open);
    if (!open) {
      setEditingGood(null);
      setReadOnly(false);
      setReadOnlyReason("");
    }
  };

  useEffect(() => {
    if (highlightedGoodId && items.some((item) => item.id === highlightedGoodId)) {
      const timer = setTimeout(() => setHighlightedGoodId(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [items, highlightedGoodId]);

  const openCreate = (): void => {
    setEditingGood(null);
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

  const visibleColumnCount: number = 6 + (SHOW_SECTION_COLUMN ? 1 : 0);

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Товары</h1>
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
            <Plus className="h-4 w-4 mr-2" /> Создать
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
          placeholder="Поиск по названию, описанию, номеру..."
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
                {renderSortableHeader("name")}
                {renderSortableHeader("item_type_name")}
                <TableHead
                  style={{ width: widths.description }}
                  className="relative"
                >
                  Описание
                  <div
                    className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary/20"
                    onMouseDown={(e) => handleMouseDown("description", e)}
                  />
                </TableHead>
                <TableHead
                  style={{ width: widths.author_name }}
                  className="relative"
                >
                  Автор
                  <div
                    className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary/20"
                    onMouseDown={(e) => handleMouseDown("author_name", e)}
                  />
                </TableHead>
                {/* ✅ P3: колонка «Раздел» скрыта флагом, код сохранён */}
                {SHOW_SECTION_COLUMN && (
                  <TableHead
                    style={{ width: widths.section_name }}
                    className="relative"
                  >
                    Раздел
                    <div
                      className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary/20"
                      onMouseDown={(e) => handleMouseDown("section_name", e)}
                    />
                  </TableHead>
                )}
                {renderSortableHeader("updated_at")}
                <TableHead style={{ width: widths.actions }} />
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.length === 0 ? (
                <TableRow>
                  <TableCell
                    colSpan={visibleColumnCount}
                    className="text-center py-8 text-muted-foreground"
                  >
                    {hasActiveFiltersOrSort || search
                      ? "Нет записей, соответствующих условиям"
                      : "Товары не найдены"}
                  </TableCell>
                </TableRow>
              ) : (
                items.map((item) => (
                  <TableRow
                    key={item.id}
                    className={
                      highlightedGoodId === item.id
                        ? "bg-yellow-100 dark:bg-yellow-900/30 transition-colors duration-300"
                        : ""
                    }
                  >
                    <TableCell
                      style={{ width: widths.name }}
                      className="py-1 align-top overflow-hidden"
                    >
                      <button
                        type="button"
                        onClick={() => openEdit(item)}
                        className="text-left text-link hover:text-link-hover hover:underline underline-offset-2 font-medium cursor-pointer w-full truncate block focus:outline-none focus:ring-2 focus:ring-link focus:ring-offset-1 rounded-sm transition-colors"
                        title={item.name}
                      >
                        {item.is_editing_locked && (
                          <Lock className="inline h-3 w-3 mr-1 text-amber-500" />
                        )}
                        {item.name}
                      </button>
                    </TableCell>
                    <TableCell
                      style={{ width: widths.item_type_name }}
                      className="py-1 align-top overflow-hidden"
                    >
                      <div
                        className="block w-full truncate"
                        title={item.item_type_name ?? undefined}
                      >
                        {item.item_type_name ?? "—"}
                      </div>
                    </TableCell>
                    <TableCell
                      style={{ width: widths.description }}
                      className="py-1 text-muted-foreground align-top overflow-hidden"
                    >
                      <div
                        className="block w-full truncate"
                        title={item.description ?? undefined}
                      >
                        {item.description || "—"}
                      </div>
                    </TableCell>
                    <TableCell
                      style={{ width: widths.author_name }}
                      className="py-1 text-muted-foreground align-top overflow-hidden"
                    >
                      <div className="block w-full truncate">
                        {item.author_name ?? "—"}
                      </div>
                    </TableCell>
                    {SHOW_SECTION_COLUMN && (
                      <TableCell
                        style={{ width: widths.section_name }}
                        className="py-1 text-muted-foreground align-top overflow-hidden"
                      >
                        <div className="block w-full truncate">
                          {item.section_name ?? "—"}
                        </div>
                      </TableCell>
                    )}
                    <TableCell
                      style={{ width: widths.updated_at }}
                      className="py-1 text-muted-foreground align-top overflow-hidden"
                    >
                      <div className="block w-full truncate">
                        {formatDate(item.updated_at)}
                      </div>
                    </TableCell>
                    <TableCell
                      style={{ width: widths.actions }}
                      className="py-1 align-top"
                    >
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 text-destructive hover:text-destructive"
                        onClick={() => setDeleteGoodId(item.id)}
                        title="Удалить"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      )}

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

      <EditGoodModal
        open={isModalOpen}
        onOpenChange={handleModalClose}
        initialData={editingGood}
        onSaved={handleGoodSaved}
        readOnly={readOnly}
        readOnlyReason={readOnlyReason}
      />

      <AlertDialog
        open={!!deleteGoodId}
        onOpenChange={(open) => !open && setDeleteGoodId(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Удалить товар?</AlertDialogTitle>
            <AlertDialogDescription>
              Товар будет помечен как удалённый (мягкое удаление). Запись
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