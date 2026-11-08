import { useState, useEffect, type FormEvent } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  Search,
  Plus,
  Trash2,
  Loader2,
  Lock,
  Copy,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
} from "lucide-react";
import { useToast } from "@/components/ui/use-toast";
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
import { useResizableColumns } from "@/components/hooks/useResizableColumns";

// ✅ Orval-хуки (Правило №9). Имена зависят от orval.config.ts —
// после npm run generate:api сверьте фактические имена.
import {
  useListRegionsSalesRegionsGet,
  useDeleteRegionSalesRegionsRegionIdDelete,
  useAcquireRegionLockSalesRegionsRegionIdLockPost,
  useReleaseRegionLockSalesRegionsRegionIdLockDelete,
  listRegionsSalesRegionsGet,
} from "@/api/generated/sales-regions/sales-regions";
import type { SalesRegionResponseSchema } from "@/api/generated/coolERP.schemas";
import { EditRegionModal } from "./EditRegionModal";

export function RegionsPage() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  // --- Состояния поиска и пагинации (Правило №22) ---
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [limit] = useState(10);

  // --- Модалка редактирования/создания и блокировка (Правило №39) ---
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingRegion, setEditingRegion] =
    useState<SalesRegionResponseSchema | null>(null);
  const [readOnly, setReadOnly] = useState(false);

  // --- Модалка копирования (без блокировки) ---
  const [copyFromData, setCopyFromData] =
    useState<SalesRegionResponseSchema | null>(null);
  const [isCopyOpen, setIsCopyOpen] = useState(false);

  // --- Удаление (Правило №16) ---
  const [deleteRegionId, setDeleteRegionId] = useState<string | null>(null);

  // --- Подсветка строки (Правило №17) ---
  const [highlightedRegionId, setHighlightedRegionId] = useState<string | null>(
    null,
  );

  // --- Orval-хуки ---
  const { data, isLoading, isError, refetch } = useListRegionsSalesRegionsGet({
    skip: (page - 1) * limit,
    limit,
    search: search || undefined,
  });

  const deleteMutation = useDeleteRegionSalesRegionsRegionIdDelete();
  const acquireLockMutation =
    useAcquireRegionLockSalesRegionsRegionIdLockPost();
  const releaseLockMutation =
    useReleaseRegionLockSalesRegionsRegionIdLockDelete();

  const regions: SalesRegionResponseSchema[] = data?.data?.items ?? [];
  const total: number = data?.data?.total ?? 0;
  const totalPages: number = Math.ceil(total / limit);

  // --- Автосброс подсветки (Правило №17) ---
  useEffect(() => {
    if (highlightedRegionId) {
      const timer = setTimeout(() => setHighlightedRegionId(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [highlightedRegionId]);

  // --- Поиск ---
  const handleSearch = (e: FormEvent) => {
    e.preventDefault();
    setPage(1);
    setSearch(searchInput);
  };

  // --- Создание: блокировка не нужна ---
  const handleCreate = () => {
    setEditingRegion(null);
    setReadOnly(false);
    setIsModalOpen(true);
  };

  // ✅ Правило №39: открытие редактирования с проверкой и захватом блокировки
  const openEdit = async (item: SalesRegionResponseSchema) => {
    setEditingRegion(item);

    // 1. Уже заблокирован → открываем в режиме только чтения
    if (item.is_editing_locked) {
      setReadOnly(true);
      setIsModalOpen(true);
      toast({
        variant: "destructive",
        title: "Регион занят",
        description:
          "Регион редактируется другим пользователем. Открыт в режиме только для чтения.",
      });
      return;
    }

    // 2. Свободен → захватываем блокировку
    try {
      await acquireLockMutation.mutateAsync({ regionId: item.id });
      setReadOnly(false);
      setIsModalOpen(true);
    } catch (error: unknown) {
      // ✅ Правило №36
      const err = error as {
        response?: { status?: number; data?: { detail?: string } };
      };

      if (err?.response?.status === 423) {
        setReadOnly(true);
        setIsModalOpen(true);
        toast({
          variant: "destructive",
          title: "Регион занят",
          description:
            "Регион редактируется другим пользователем. Открыт в режиме только для чтения.",
        });
      } else {
        toast({
          variant: "destructive",
          title: "Ошибка блокировки",
          description:
            err?.response?.data?.detail || "Не удалось открыть регион",
        });
      }
    }
  };

  // ✅ Правило №39: освобождение блокировки при закрытии модалки редактирования
  const handleModalClose = async (open: boolean) => {
    if (!open && editingRegion && !readOnly) {
      try {
        await releaseLockMutation.mutateAsync({ regionId: editingRegion.id });
      } catch {
        // Ошибки освобождения игнорируются (таймаут 30 минут снимет блокировку)
      }
    }

    setIsModalOpen(open);
    if (!open) {
      setEditingRegion(null);
      setReadOnly(false);
    }
  };

  // --- Копирование (без блокировки) ---
  const handleCopy = (item: SalesRegionResponseSchema) => {
    setCopyFromData(item);
    setIsCopyOpen(true);
  };

  const handleCopyModalClose = (open: boolean) => {
    setIsCopyOpen(open);
    if (!open) {
      setCopyFromData(null);
    }
  };

  // ✅ Умная навигация (Правило №18, №23)
  const handleRegionSaved = async (
    newId: string,
    newName: string,
  ): Promise<void> => {
    const result = await refetch();
    const currentItems: SalesRegionResponseSchema[] =
      result.data?.data?.items ?? [];

    if (currentItems.some((item) => item.id === newId)) {
      setHighlightedRegionId(newId);
      toast({
        title: "Сохранено",
        description: `Регион "${newName}" обновлён`,
      });
      return;
    }

    try {
      const allData = await listRegionsSalesRegionsGet({
        limit: 1000,
        skip: 0,
      });
      const allItems: SalesRegionResponseSchema[] = allData?.data?.items ?? [];
      const itemIndex: number = allItems.findIndex(
        (item) => item.id === newId,
      );

      if (itemIndex < 0) {
        toast({
          variant: "destructive",
          title: "Ошибка",
          description: "Не удалось найти сохранённый регион",
        });
        return;
      }

      const targetPage: number = Math.floor(itemIndex / limit) + 1;
      toast({
        title: "Сохранено",
        description: `Регион "${newName}" на странице ${targetPage}`,
        action: (
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              setPage(targetPage);
              setTimeout(() => setHighlightedRegionId(newId), 500);
            }}
          >
            Перейти
          </Button>
        ),
      });
    } catch {
      toast({
        variant: "destructive",
        title: "Ошибка",
        description: "Не удалось найти сохранённый регион",
      });
    }
  };

  // ✅ Удаление с обработкой 423 (Правило №16 + №39)
  const handleDelete = () => {
    if (!deleteRegionId) return;

    deleteMutation.mutate(
      { regionId: deleteRegionId },
      {
        onSuccess: async () => {
          toast({ title: "Удалено", description: "Регион удалён" });
          queryClient.invalidateQueries({ queryKey: ["sales-regions"] });
          await refetch(); // Правило №25
          setDeleteRegionId(null);
        },
        onError: (error: unknown) => {
          const err = error as {
            response?: { status?: number; data?: { detail?: string } };
          };
          let message: string =
            err?.response?.data?.detail || "Не удалось удалить регион";

          if (err?.response?.status === 423) {
            message =
              "Регион заблокирован другим пользователем и не может быть удалён";
          }

          toast({
            variant: "destructive",
            title: "Ошибка удаления",
            description: message,
          });
        },
      },
    );
  };

  // ✅ Изменяемая ширина колонок (Правило №29)
  const columns = [
    { id: "name", initialWidth: 200, minWidth: 140 },
    { id: "capital", initialWidth: 160, minWidth: 120 },
    { id: "code", initialWidth: 110, minWidth: 90 },
    { id: "area", initialWidth: 160, minWidth: 120 },
    { id: "updated_at", initialWidth: 150, minWidth: 120 },
    { id: "actions", initialWidth: 100, minWidth: 80 },
  ];
  const { widths, handleMouseDown, resetWidths } = useResizableColumns(
    columns,
    "regions-table-widths",
  );

  if (isError) {
    return <div className="p-4 text-destructive">Ошибка загрузки данных</div>;
  }

  return (
    <div className="container mx-auto px-4 py-3">
      {/* Заголовок и панель действий */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-2 mb-2">
        <div>
          <h1 className="text-xl font-bold">Регионы</h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            Всего: {total}
          </p>
        </div>
        <div className="flex gap-2 w-full md:w-auto">
          <form
            onSubmit={handleSearch}
            className="flex gap-2 flex-1 md:flex-initial"
          >
            <Input
              placeholder="Поиск региона..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              className="w-full md:w-64"
            />
            <Button type="submit" variant="secondary">
              <Search className="h-4 w-4 mr-2" /> Найти
            </Button>
          </form>
          <Button onClick={handleCreate}>
            <Plus className="h-4 w-4 mr-2" /> Создать
          </Button>
        </div>
      </div>

      {/* Таблица (Правило №13) */}
      <div className="rounded-md border bg-card">
        <div className="flex justify-end p-2 border-b">
          <Button
            variant="ghost"
            size="sm"
            onClick={resetWidths}
            className="text-xs"
          >
            Сбросить ширину
          </Button>
        </div>

        <Table className="table-fixed w-full">
          <TableHeader>
            <TableRow className="h-10 hover:bg-transparent">
              <TableHead
                className="relative"
                style={{ width: `${widths.name}px` }}
              >
                Название
                <div
                  className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary/20 active:bg-primary/40 transition-colors"
                  onMouseDown={(e) => handleMouseDown("name", e)}
                />
              </TableHead>
              <TableHead
                className="relative"
                style={{ width: `${widths.capital}px` }}
              >
                Адм. центр
                <div
                  className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary/20"
                  onMouseDown={(e) => handleMouseDown("capital", e)}
                />
              </TableHead>
              <TableHead
                className="relative"
                style={{ width: `${widths.code}px` }}
              >
                Код
                <div
                  className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary/20"
                  onMouseDown={(e) => handleMouseDown("code", e)}
                />
              </TableHead>
              <TableHead
                className="relative"
                style={{ width: `${widths.area}px` }}
              >
                Область / округ
                <div
                  className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary/20"
                  onMouseDown={(e) => handleMouseDown("area", e)}
                />
              </TableHead>
              <TableHead
                className="relative"
                style={{ width: `${widths.updated_at}px` }}
              >
                Обновлено
                <div
                  className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary/20"
                  onMouseDown={(e) => handleMouseDown("updated_at", e)}
                />
              </TableHead>
              <TableHead style={{ width: `${widths.actions}px` }} />
            </TableRow>
          </TableHeader>

          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin mx-auto" />
                </TableCell>
              </TableRow>
            ) : regions.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={6}
                  className="text-center text-muted-foreground py-8"
                >
                  Регионы не найдены
                </TableCell>
              </TableRow>
            ) : (
              regions.map((item) => (
                <TableRow
                  key={item.id}
                  className={
                    highlightedRegionId === item.id
                      ? "bg-yellow-100 dark:bg-yellow-900/30 transition-colors duration-300"
                      : ""
                  }
                >
                  {/* ✅ Правило №39: название-ссылка + иконка замка */}
                  <TableCell
                    style={{ width: `${widths.name}px` }}
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
                    style={{ width: `${widths.capital}px` }}
                    className="py-1 align-top overflow-hidden text-muted-foreground"
                  >
                    <div
                      className="block w-full truncate"
                      title={item.capital || undefined}
                    >
                      {item.capital || "—"}
                    </div>
                  </TableCell>

                  <TableCell
                    style={{ width: `${widths.code}px` }}
                    className="py-1 align-top overflow-hidden text-muted-foreground"
                  >
                    <div
                      className="block w-full truncate"
                      title={item.code || undefined}
                    >
                      {item.code || "—"}
                    </div>
                  </TableCell>

                  <TableCell
                    style={{ width: `${widths.area}px` }}
                    className="py-1 align-top overflow-hidden text-muted-foreground"
                  >
                    <div
                      className="block w-full truncate"
                      title={item.area || undefined}
                    >
                      {item.area || "—"}
                    </div>
                  </TableCell>

                  <TableCell
                    style={{ width: `${widths.updated_at}px` }}
                    className="py-1 align-top overflow-hidden text-muted-foreground"
                  >
                    <div className="block w-full truncate">
                      {new Date(item.updated_at).toLocaleString("ru-RU", {
                        day: "2-digit",
                        month: "2-digit",
                        year: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </div>
                  </TableCell>

                  {/* ✅ Колонка Действия: копирование + удаление */}
                  <TableCell
                    style={{ width: `${widths.actions}px` }}
                    className="py-1 align-top"
                  >
                    <div className="flex gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7"
                        onClick={() => handleCopy(item)}
                        title="Копировать"
                      >
                        <Copy className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 text-destructive hover:text-destructive hover:bg-destructive/10"
                        onClick={() => setDeleteRegionId(item.id)}
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

      {/* Пагинация */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-1 mt-3">
          <Button size="sm" variant="outline" className="h-8 w-8 p-0" disabled={page === 1} onClick={() => setPage(1)}>
            <ChevronsLeft className="h-4 w-4" />
          </Button>
          <Button size="sm" variant="outline" className="h-8 w-8 p-0" disabled={page === 1} onClick={() => setPage(page - 1)}>
            <ChevronLeft className="h-4 w-4" />
          </Button>
          {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
            let pageNum: number = i + 1;
            if (totalPages > 5 && page > 3) pageNum = page - 2 + i;
            if (pageNum > totalPages || pageNum < 1) return null;
            return (
              <Button
                key={pageNum}
                size="sm"
                variant={page === pageNum ? "default" : "outline"}
                className="h-8 w-8 p-0"
                onClick={() => setPage(pageNum)}
              >
                {pageNum}
              </Button>
            );
          })}
          <Button size="sm" variant="outline" className="h-8 w-8 p-0" disabled={page === totalPages} onClick={() => setPage(page + 1)}>
            <ChevronRight className="h-4 w-4" />
          </Button>
          <Button size="sm" variant="outline" className="h-8 w-8 p-0" disabled={page === totalPages} onClick={() => setPage(totalPages)}>
            <ChevronsRight className="h-4 w-4" />
          </Button>
        </div>
      )}

      {/* Модалка редактирования/создания (с блокировкой, Правило №39) */}
      <EditRegionModal
        open={isModalOpen}
        onOpenChange={handleModalClose}
        initialData={editingRegion}
        onSaved={handleRegionSaved}
        readOnly={readOnly}
      />

      {/* Модалка копирования (без блокировки) */}
      {isCopyOpen && copyFromData && (
        <EditRegionModal
          key={`copy-${copyFromData.id}`}
          open={isCopyOpen}
          onOpenChange={handleCopyModalClose}
          initialData={null}
          copyFromData={copyFromData}
          onSaved={handleRegionSaved}
          readOnly={false}
        />
      )}

      {/* Подтверждение удаления (Правило №16) */}
      <AlertDialog
        open={!!deleteRegionId}
        onOpenChange={(open) => !open && setDeleteRegionId(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Удалить регион?</AlertDialogTitle>
            <AlertDialogDescription>
              Регион будет удалён. Ссылки на него в других документах могут
              стать недействительными. Это действие нельзя отменить.
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
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                "Удалить"
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}