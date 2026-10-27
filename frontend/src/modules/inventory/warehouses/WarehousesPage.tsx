import { useState, useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  Search,
  Plus,
  Trash2,
  Loader2,
  Lock,
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

// ✅ Orval-хуки (Правило №9). Имена зависят от конфигурации orval.config.ts.
// После перегенерации (npm run generate:api) уточните фактические имена.
import {
  useListWarehousesInventoryWarehousesGet,
  useDeleteWarehouseInventoryWarehousesWarehouseIdDelete,
  useAcquireWarehouseLockInventoryWarehousesWarehouseIdLockPost,
  useReleaseWarehouseLockInventoryWarehousesWarehouseIdLockDelete,
  listWarehousesInventoryWarehousesGet,
} from "@/api/generated/inventory-warehouses/inventory-warehouses";
import type { InvWarehouseResponseSchema } from "@/api/generated/fastAPI.schemas";
import { EditWarehouseModal } from "./EditWarehouseModal";

export function WarehousesPage() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  // --- Состояния (Правило №22) ---
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [limit] = useState(10);

  // --- Модалка и блокировка (Правило №39) ---
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingWarehouse, setEditingWarehouse] =
    useState<InvWarehouseResponseSchema | null>(null);
  const [readOnly, setReadOnly] = useState(false);

  // --- Удаление (Правило №16) ---
  const [deleteWarehouseId, setDeleteWarehouseId] = useState<string | null>(
    null,
  );

  // --- Подсветка (Правило №17) ---
  const [highlightedWarehouseId, setHighlightedWarehouseId] = useState<
    string | null
  >(null);

  // --- Orval-хуки ---
  const { data, isLoading, isError, refetch } =
    useListWarehousesInventoryWarehousesGet({
      skip: (page - 1) * limit,
      limit,
      search: search || undefined,
    });

  const deleteMutation = useDeleteWarehouseInventoryWarehousesWarehouseIdDelete();
  const acquireLockMutation =
    useAcquireWarehouseLockInventoryWarehousesWarehouseIdLockPost();
  const releaseLockMutation =
    useReleaseWarehouseLockInventoryWarehousesWarehouseIdLockDelete();

  const warehouses = data?.data?.items ?? [];
  const total = data?.data?.total ?? 0;
  const totalPages = Math.ceil(total / limit);

  // --- Автосброс подсветки (Правило №17) ---
  useEffect(() => {
    if (highlightedWarehouseId) {
      const timer = setTimeout(() => setHighlightedWarehouseId(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [highlightedWarehouseId]);

  // --- Обработчики ---
  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    setSearch(searchInput);
  };

  const handleCreate = () => {
    setEditingWarehouse(null);
    setReadOnly(false);
    setIsModalOpen(true);
  };

  // ✅ Правило №39: Открытие с проверкой и захватом блокировки
  const openEdit = async (item: InvWarehouseResponseSchema) => {
    setEditingWarehouse(item);

    // 1. Если документ уже заблокирован — сразу открываем в readOnly
    if (item.is_editing_locked) {
      setReadOnly(true);
      setIsModalOpen(true);
      toast({
        variant: "destructive",
        title: "Склад занят",
        description:
          "Склад редактируется другим пользователем. Открыт в режиме только для чтения.",
      });
      return;
    }

    // 2. Документ свободен — пытаемся захватить блокировку
    try {
      await acquireLockMutation.mutateAsync({ warehouseId: item.id });
      setReadOnly(false);
      setIsModalOpen(true);
    } catch (error: unknown) {
      // ✅ Правило №36: безопасная обработка ошибок
      const err = error as {
        response?: { status?: number; data?: { detail?: string } };
      };
      if (err?.response?.status === 423) {
        // Блокировка захвачена между проверкой и вызовом — открываем в readOnly
        setReadOnly(true);
        setIsModalOpen(true);
        toast({
          variant: "destructive",
          title: "Склад занят",
          description:
            "Склад редактируется другим пользователем. Открыт в режиме только для чтения.",
        });
      } else {
        toast({
          variant: "destructive",
          title: "Ошибка блокировки",
          description:
            err?.response?.data?.detail || "Не удалось заблокировать склад",
        });
      }
    }
  };

  // ✅ Правило №39: Освобождение блокировки при закрытии модалки
  const handleModalClose = async (open: boolean) => {
    if (!open && editingWarehouse && !readOnly) {
      try {
        await releaseLockMutation.mutateAsync({
          warehouseId: editingWarehouse.id,
        });
      } catch {
        // ✅ Ошибки освобождения игнорируются (таймаут 30 минут снимет блокировку)
      }
    }
    setIsModalOpen(open);
    if (!open) {
      setEditingWarehouse(null);
      setReadOnly(false);
    }
  };

  // ✅ Умная навигация (Правило №18, 23)
  const handleWarehouseSaved = async (newId: string, newName: string) => {
    const result = await refetch();
    const currentItems = result.data?.data?.items || [];
    const itemExists = currentItems.some(
      (i: InvWarehouseResponseSchema) => i.id === newId,
    );

    if (itemExists) {
      setHighlightedWarehouseId(newId);
      toast({ title: "Сохранено", description: `Склад "${newName}" обновлён` });
      return;
    }

    try {
      const allData = await listWarehousesInventoryWarehousesGet({
        limit: 1000,
        skip: 0,
      });
      const allItems = allData?.data?.items ?? [];
      const itemIndex = allItems.findIndex(
        (i: InvWarehouseResponseSchema) => i.id === newId,
      );
      const targetPage = Math.floor(itemIndex / limit) + 1;
      toast({
        title: "Сохранено",
        description: `Склад "${newName}" находится на странице ${targetPage}`,
        action: (
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              setPage(targetPage);
              setTimeout(() => setHighlightedWarehouseId(newId), 500);
            }}
          >
            Перейти
          </Button>
        ),
      });
    } catch (error) {
      console.error("Ошибка поиска записи:", error);
      toast({
        variant: "destructive",
        title: "Ошибка",
        description: "Не удалось найти склад",
      });
    }
  };

  // ✅ Удаление с обработкой 423 (Правило №16 + Правило №39)
  const handleDelete = () => {
    if (!deleteWarehouseId) return;
    deleteMutation.mutate(
      { warehouseId: deleteWarehouseId },
      {
        onSuccess: async () => {
          toast({ title: "Удалено", description: "Склад успешно удалён" });
          queryClient.invalidateQueries({ queryKey: ["inventory-warehouses"] });
          await refetch(); // Правило №25
          setDeleteWarehouseId(null);
        },
        onError: (error: unknown) => {
          const err = error as {
            response?: { status?: number; data?: { detail?: string } };
          };
          const status = err?.response?.status;
          let message =
            err?.response?.data?.detail || "Не удалось удалить склад";
          if (status === 423) {
            message =
              "Склад заблокирован другим пользователем и не может быть удалён";
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
    { id: "name", initialWidth: 180, minWidth: 120 },
    { id: "description", initialWidth: 200, minWidth: 100 },
    { id: "section_name", initialWidth: 160, minWidth: 100 },
    { id: "author_name", initialWidth: 150, minWidth: 100 },
    { id: "updated_at", initialWidth: 140, minWidth: 100 },
    { id: "actions", initialWidth: 80, minWidth: 60 },
  ];
  const { widths, handleMouseDown, resetWidths } = useResizableColumns(
    columns,
    "warehouses-table-widths",
  );

  if (isError)
    return <div className="p-4 text-destructive">Ошибка загрузки данных</div>;

  return (
    <div className="container mx-auto px-4 py-3">
      {/* Заголовок (Правило №11) */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-2 mb-2">
        <div>
          <h1 className="text-xl font-bold">Склады</h1>
          <p className="text-xs text-muted-foreground mt-0.5">Всего: {total}</p>
        </div>
        <div className="flex gap-2 w-full md:w-auto">
          <form
            onSubmit={handleSearch}
            className="flex gap-2 flex-1 md:flex-initial"
          >
            <Input
              placeholder="Поиск склада..."
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
          <Button variant="ghost" size="sm" onClick={resetWidths} className="text-xs">
            Сбросить ширину
          </Button>
        </div>
        <Table className="table-fixed w-full">
          <TableHeader>
            <TableRow className="h-10 hover:bg-transparent">
              <TableHead className="relative" style={{ width: `${widths.name}px` }}>
                Название
                <div
                  className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary/20 active:bg-primary/40 transition-colors"
                  onMouseDown={(e) => handleMouseDown("name", e)}
                />
              </TableHead>
              <TableHead className="relative" style={{ width: `${widths.description}px` }}>
                Описание
                <div
                  className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary/20 active:bg-primary/40 transition-colors"
                  onMouseDown={(e) => handleMouseDown("description", e)}
                />
              </TableHead>
              <TableHead className="relative" style={{ width: `${widths.section_name}px` }}>
                Раздел
                <div
                  className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary/20 active:bg-primary/40 transition-colors"
                  onMouseDown={(e) => handleMouseDown("section_name", e)}
                />
              </TableHead>
              <TableHead className="relative" style={{ width: `${widths.author_name}px` }}>
                Автор
                <div
                  className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary/20 active:bg-primary/40 transition-colors"
                  onMouseDown={(e) => handleMouseDown("author_name", e)}
                />
              </TableHead>
              <TableHead className="relative" style={{ width: `${widths.updated_at}px` }}>
                Обновлено
                <div
                  className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary/20 active:bg-primary/40 transition-colors"
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
            ) : warehouses.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={6}
                  className="text-center text-muted-foreground py-8"
                >
                  Склады не найдены
                </TableCell>
              </TableRow>
            ) : (
              warehouses.map((item) => (
                <TableRow
                  key={item.id}
                  className={
                    highlightedWarehouseId === item.id
                      ? "bg-yellow-100 dark:bg-yellow-900/30 transition-colors duration-300"
                      : ""
                  }
                >
                  {/* ✅ Правило №39: Название как кликабельная ссылка */}
                  <TableCell
                    style={{ width: `${widths.name}px` }}
                    className="py-1 align-top overflow-hidden"
                  >
                    <button
                      type="button"
                      onClick={() => openEdit(item)}
                      className="text-left text-blue-600 hover:text-blue-800 hover:underline underline-offset-2 font-medium cursor-pointer w-full truncate block focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1 rounded-sm transition-colors"
                      title={item.name}
                    >
                      {/* ✅ Иконка замка при блокировке */}
                      {item.is_editing_locked && (
                        <Lock className="inline h-3 w-3 mr-1 text-amber-500" />
                      )}
                      {item.name}
                    </button>
                  </TableCell>
                  <TableCell
                    style={{ width: `${widths.description}px` }}
                    className="py-1 text-muted-foreground align-top overflow-hidden"
                  >
                    <div
                      title={item.description || undefined}
                      className="block w-full truncate"
                    >
                      {item.description || "—"}
                    </div>
                  </TableCell>
                  {/* ✅ Правило №42: денормализованное имя раздела */}
                  <TableCell
                    style={{ width: `${widths.section_name}px` }}
                    className="py-1 text-muted-foreground align-top overflow-hidden"
                  >
                    <div className="block w-full truncate">
                      {item.section_name ?? "—"}
                    </div>
                  </TableCell>
                  {/* ✅ Правило №42: денормализованное имя автора */}
                  <TableCell
                    style={{ width: `${widths.author_name}px` }}
                    className="py-1 text-muted-foreground align-top overflow-hidden"
                  >
                    <div className="block w-full truncate">
                      {item.author_name ?? "—"}
                    </div>
                  </TableCell>
                  <TableCell
                    style={{ width: `${widths.updated_at}px` }}
                    className="py-1 text-muted-foreground align-top overflow-hidden"
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
                  {/* ✅ Правило №39: Колонка Действия — только удаление */}
                  <TableCell
                    style={{ width: `${widths.actions}px` }}
                    className="py-1 align-top"
                  >
                    <div className="flex gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 text-destructive hover:text-destructive hover:bg-destructive/10"
                        onClick={() => setDeleteWarehouseId(item.id)}
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

      {/* Пагинация (Правило №15) */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-1 mt-3">
          <Button size="sm" variant="outline" className="h-8 w-8 p-0" disabled={page === 1} onClick={() => setPage(1)}>
            <ChevronsLeft className="h-4 w-4" />
          </Button>
          <Button size="sm" variant="outline" className="h-8 w-8 p-0" disabled={page === 1} onClick={() => setPage(page - 1)}>
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

      {/* Модалка создания/редактирования (Правило №35, №39) */}
      <EditWarehouseModal
        open={isModalOpen}
        onOpenChange={handleModalClose}
        initialData={editingWarehouse}
        onSaved={handleWarehouseSaved}
        readOnly={readOnly}
      />

      {/* AlertDialog для удаления (Правило №16) */}
      <AlertDialog
        open={!!deleteWarehouseId}
        onOpenChange={(open) => !open && setDeleteWarehouseId(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Удалить склад?</AlertDialogTitle>
            <AlertDialogDescription>
              Это действие нельзя отменить. Связанные документы могут быть затронуты.
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