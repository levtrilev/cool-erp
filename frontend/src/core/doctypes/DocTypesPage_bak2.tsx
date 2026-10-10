import { useState, useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  Plus,
  Search,
  Trash2,
  Loader2,
  CheckCircle2,
  XCircle,
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

import { useResizableColumns } from "@/components/hooks/useResizableColumns";
import {
  useGetDoctypesDoctypesGet,
  useDeleteDoctypeDoctypesDoctypeIdDelete,
} from "@/api/generated/doctypes/doctypes";
import { getDoctypesDoctypesGet } from "@/api/generated/doctypes/doctypes";
import type { DoctypeResponseSchema } from "@/api/generated/fastAPI.schemas";

// ✅ Импорт вынесенного компонента модального окна
import { EditDoctypeModal } from "./EditDoctypeModal";

export const DoctypesPage = () => {
    const queryClient = useQueryClient();
  const { toast } = useToast();
  const limit = 10;

  // ✅ Правило №22: Структура состояний
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);

  // ✅ Состояния только для управления открытием модалки и передачи данных
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingDoctype, setEditingDoctype] =
    useState<DoctypeResponseSchema | null>(null);

  const [deleteDoctypeId, setDeleteDoctypeId] = useState<string | null>(null);
  const [highlightedDoctypeId, setHighlightedDoctypeId] = useState<
    string | null
  >(null);

  // ✅ Правило №29: Изменяемые колонки
  const columns = [
    { id: "doctype", initialWidth: 150, minWidth: 100 },
    { id: "doctype_name", initialWidth: 250, minWidth: 150 },
    { id: "domain", initialWidth: 200, minWidth: 150 },
    { id: "is_active", initialWidth: 100, minWidth: 80 },
    { id: "tenants", initialWidth: 200, minWidth: 150 },
    { id: "actions", initialWidth: 50, minWidth: 50 },
  ];
  const { widths, handleMouseDown, resetWidths } = useResizableColumns(
    columns,
    "doctypes-table-widths",
  );

  // ✅ Правило №9: Orval хуки
  const { data, isLoading, refetch } = useGetDoctypesDoctypesGet({
    skip: (page - 1) * limit,
    limit,
    search: search || undefined,
  });

  const deleteMutation = useDeleteDoctypeDoctypesDoctypeIdDelete();

  // ✅ Правило №18 и №23: Умная навигация и подсветка
  const handleSaved = async (id: string) => {
    await refetch();
    const currentItems = data?.data?.items || [];
    if (currentItems.some((item) => item.id === id)) {
      setHighlightedDoctypeId(id);
      setTimeout(() => setHighlightedDoctypeId(null), 3000);
      toast({ title: "Успешно сохранено" });
    } else {
      const fullList = await getDoctypesDoctypesGet({ limit: 1000, skip: 0 });
      const foundIndex = (fullList.data?.items || []).findIndex(
        (item) => item.id === id,
      );
      if (foundIndex !== -1) {
        const targetPage = Math.ceil((foundIndex + 1) / limit);
        toast({
          title: "Сохранено",
          description: `На странице ${targetPage}`,
          action: (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage(targetPage)}
            >
              Перейти
            </Button>
          ),
        });
      }
    }
  };

  // ✅ Правило №25: refetch() после удаления
  const handleDelete = async () => {
    if (!deleteDoctypeId) return;
    try {
      await deleteMutation.mutateAsync({ doctypeId: deleteDoctypeId });
      await refetch();
      setDeleteDoctypeId(null);
      toast({ title: "Удалено" });
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      toast({
        variant: "destructive",
        title: "Ошибка удаления",
        description: err?.response?.data?.detail || String(error),
      });
    }
  };

  // ✅ Правило №17: Подсветка через useEffect
  useEffect(() => {
    if (
      highlightedDoctypeId &&
      data?.data?.items?.some((i) => i.id === highlightedDoctypeId)
    ) {
      const timer = setTimeout(() => setHighlightedDoctypeId(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [data, highlightedDoctypeId]);

  //   const openEdit = (item: DoctypeResponseSchema) => {
  //     setEditingDoctype(item);
  //     setIsModalOpen(true);
  //   };
  const openEdit = (item: DoctypeResponseSchema) => {
    // ✅ СИНХРОННАЯ установка домена в кэш ДО открытия модалки
    // Это гарантирует, что ReferenceSelect сразу найдёт нужный item
    if (item.domain_id && item.domain_name) {
      const currentData = queryClient.getQueryData(["domains"]) as
        | {
            items?: Array<{ id: string; name?: string; description?: string }>;
            total?: number;
          }
        | undefined;

      if (currentData && Array.isArray(currentData.items)) {
        const exists = currentData.items.some(
          (domainItem) => domainItem.id === item.domain_id,
        );

        if (!exists) {
          queryClient.setQueryData(["domains"], {
            ...currentData,
            items: [
              {
                id: item.domain_id,
                name: item.domain_name,
                description: "",
              },
              ...currentData.items,
            ],
          });
        }
      } else {
        queryClient.setQueryData(["domains"], {
          items: [
            {
              id: item.domain_id,
              name: item.domain_name,
              description: "",
            },
          ],
          total: 1,
        });
      }
    }

    setEditingDoctype(item);
    // reset({
    //   domain_id: item.domain_id,
    //   doctype: item.doctype,
    //   doctype_name: item.doctype_name,
    //   description: item.description || "",
    //   is_active: item.is_active ?? true,
    //   tenant_ids: item.tenant_ids ?? [],
    // });
    setIsModalOpen(true);
  };
  const items = data?.data?.items || [];

  return (
    <div className="container mx-auto px-4 py-3">
      {/* ✅ Правило №11 */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-2 mb-2">
        <div>
          <h1 className="text-xl font-bold">Типы документов</h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            Всего: {data?.data?.total || 0}
          </p>
        </div>
        <Button
          onClick={() => {
            setEditingDoctype(null); // null = режим создания
            setIsModalOpen(true);
          }}
        >
          <Plus className="mr-2 h-4 w-4" /> Создать
        </Button>
      </div>

      {/* ✅ Правило №12: Поиск через form */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          setSearch(searchInput);
          setPage(1);
        }}
        className="flex gap-2 mb-2"
      >
        <div className="relative flex-1 max-w-sm">
          <Input
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Поиск по имени или коду..."
            className="pl-9"
          />
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        </div>
        <Button type="submit" variant="secondary">
          Найти
        </Button>
      </form>

      {/* ✅ Правила №13, №14, №29: Таблица */}
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
              <TableHead className="relative" style={{ width: widths.doctype }}>
                Код
                <div
                  className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary/20"
                  onMouseDown={(e) => handleMouseDown("doctype", e)}
                />
              </TableHead>
              <TableHead
                className="relative"
                style={{ width: widths.doctype_name }}
              >
                Название
                <div
                  className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary/20"
                  onMouseDown={(e) => handleMouseDown("doctype_name", e)}
                />
              </TableHead>
              <TableHead className="relative" style={{ width: widths.domain }}>
                Домен
                <div
                  className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary/20"
                  onMouseDown={(e) => handleMouseDown("domain", e)}
                />
              </TableHead>
              <TableHead
                className="relative"
                style={{ width: widths.is_active }}
              >
                Активен
                <div
                  className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary/20"
                  onMouseDown={(e) => handleMouseDown("is_active", e)}
                />
              </TableHead>
              <TableHead className="relative" style={{ width: widths.tenants }}>
                Организации
                <div
                  className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary/20"
                  onMouseDown={(e) => handleMouseDown("tenants", e)}
                />
              </TableHead>
              <TableHead style={{ width: widths.actions }}></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin mx-auto" />
                </TableCell>
              </TableRow>
            ) : items.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={6}
                  className="text-center text-muted-foreground py-8"
                >
                  Не найдено
                </TableCell>
              </TableRow>
            ) : (
              items.map((item) => (
                <TableRow
                  key={item.id}
                  className={
                    highlightedDoctypeId === item.id
                      ? "bg-yellow-100 dark:bg-yellow-900/30 transition-colors duration-300"
                      : ""
                  }
                >
                  <TableCell
                    className="py-1 align-top overflow-hidden"
                    style={{ width: widths.doctype }}
                  >
                    <button
                      onClick={() => openEdit(item)}
                      title={item.doctype}
                      className="block w-full text-left text-blue-600 hover:text-blue-800 hover:underline cursor-pointer font-medium truncate"
                    >
                      {item.doctype}
                    </button>
                  </TableCell>
                  <TableCell
                    className="py-1 align-top overflow-hidden"
                    style={{ width: widths.doctype_name }}
                  >
                    <div
                      title={item.doctype_name}
                      className="block w-full truncate"
                    >
                      {item.doctype_name}
                    </div>
                  </TableCell>
                  <TableCell
                    className="py-1 align-top overflow-hidden"
                    style={{ width: widths.domain }}
                  >
                    <div
                      title={item.domain_name || " "}
                      className="block w-full truncate"
                    >
                      {item.domain_name || "—"}
                    </div>
                  </TableCell>
                  <TableCell
                    className="py-1 align-top"
                    style={{ width: widths.is_active }}
                  >
                    {item.is_active ? (
                      <CheckCircle2 className="h-4 w-4 text-green-600" />
                    ) : (
                      <XCircle className="h-4 w-4 text-muted-foreground" />
                    )}
                  </TableCell>
                  <TableCell
                    className="py-1 align-top overflow-hidden"
                    style={{ width: widths.tenants }}
                  >
                    <span className="text-xs text-muted-foreground">
                      {item.tenant_ids?.length || 0} орг.
                    </span>
                  </TableCell>
                  <TableCell
                    className="py-1 align-top"
                    style={{ width: widths.actions }}
                  >
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-destructive"
                      onClick={() => setDeleteDoctypeId(item.id)}
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

      {/* ✅ Вынесенный компонент модального окна */}
      <EditDoctypeModal
        open={isModalOpen}
        onOpenChange={setIsModalOpen}
        initialData={editingDoctype}
        onSaved={handleSaved}
      />

      {/* ✅ Правило №16: AlertDialog для удаления */}
      <AlertDialog
        open={!!deleteDoctypeId}
        onOpenChange={(open) => !open && setDeleteDoctypeId(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Удалить тип документа?</AlertDialogTitle>
            <AlertDialogDescription>
              Это действие нельзя отменить. Связанные полномочия могут быть
              затронуты.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Отмена</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              disabled={deleteMutation.isPending}
              className="bg-destructive text-destructive-foreground"
            >
              {deleteMutation.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                "Удалить"
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};
