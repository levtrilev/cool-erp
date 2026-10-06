import { useState, useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  Plus,
  Search,
  Trash2,
  Loader2,
  CheckCircle2,
  XCircle,
  PauseCircle,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
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
import { TenantMultiSelect } from "@/core/tenants/TenantMultiSelect";
import { useResizableColumns } from "@/components/hooks/useResizableColumns";

// ✅ Правило №9 и №10: Orval хуки и типы
import {
  useGetDoctypesDoctypesGet,
  useCreateDoctypeDoctypesPost,
  useUpdateDoctypeDoctypesDoctypeIdPut,
  useDeleteDoctypeDoctypesDoctypeIdDelete,
} from "@/api/generated/doctypes/doctypes";
import { getDoctypesDoctypesGet } from "@/api/generated/doctypes/doctypes";
import { getDomainsDomainsGet } from "@/api/generated/domains/domains";
import type {
  DoctypeResponseSchema,
  DoctypeCreateSchema,
  DoctypeUpdateSchema,
} from "@/api/generated/fastAPI.schemas";
import { ReferenceSelect } from "@/lib/reusable/ReferenceSelect";

// ✅ Zod-схема под новые поля модели
const doctypeSchema = z.object({
  domain_id: z.string().uuid("Выберите домен"),
  doctype: z.string().min(2, "Минимум 2 символа (например, invoices)"),
  doctype_name: z.string().min(2, "Минимум 2 символа"),
  description: z.string().optional(),
  is_active: z.boolean().optional(),
  // is_active: z.boolean().default(true),
  tenant_ids: z.array(z.string().uuid()).optional(),
  // tenant_ids: z.array(z.string().uuid()).default([]),
});

type DoctypeFormData = z.infer<typeof doctypeSchema>;

export const DoctypesPage = () => {
  // ✅ ЯВНЫЕ ЗНАЧЕНИЯ ПО УМОЛЧАНИЮ ДЛЯ СОЗДАНИЯ НОВОЙ ЗАПИСИ
  // Эта константа гарантирует, что форма всегда сбрасывается в чистое состояние
  const CREATE_DEFAULTS: DoctypeFormData = {
    domain_id: "",
    doctype: "",
    doctype_name: "",
    description: "",
    is_active: true,
    tenant_ids: [], // ✅ Гарантированно пустой массив при создании
  };

  const queryClient = useQueryClient();
  const { toast } = useToast();
  const limit = 10;

  // ✅ Правило №22: Структура состояний
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
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
  const createMutation = useCreateDoctypeDoctypesPost();
  const updateMutation = useUpdateDoctypeDoctypesDoctypeIdPut();
  const deleteMutation = useDeleteDoctypeDoctypesDoctypeIdDelete();

  const {
    control,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<DoctypeFormData>({
    resolver: zodResolver(doctypeSchema),
    defaultValues: CREATE_DEFAULTS,
  });

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

  // ✅ Правило №24: invalidateQueries ДО закрытия модалки
  const onSubmit = async (formData: DoctypeFormData) => {
    try {
      if (editingDoctype) {
        await updateMutation.mutateAsync({
          doctypeId: editingDoctype.id,
          data: formData as DoctypeUpdateSchema,
        });
        await queryClient.invalidateQueries({ queryKey: ["doctypes"] });
        setEditModalOpen(false);
        setEditingDoctype(null);
        await handleSaved(editingDoctype.id);
      } else {
        const res = await createMutation.mutateAsync({
          data: formData as DoctypeCreateSchema,
        });
        await queryClient.invalidateQueries({ queryKey: ["doctypes"] });
        setIsCreateOpen(false);
        await handleSaved(res.data!.id);
      }
      reset();
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Ошибка",
        description: "Не удалось сохранить тип документа: " + String(error),
      });
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
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Ошибка удаления типа документа",
        description: String(error),
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

  const openEdit = (item: DoctypeResponseSchema) => {
    setEditingDoctype(item);
    reset({
      domain_id: item.domain_id,
      doctype: item.doctype,
      doctype_name: item.doctype_name,
      description: item.description || "",
      is_active: item.is_active ?? true, // ✅ Страховка от null/undefined
      tenant_ids: item.tenant_ids ?? [], // ✅ Страховка от null/undefined
    });
    setEditModalOpen(true);
  };

  const items = data?.data?.items || [];

  return (
    <div className="container mx-auto px-4 py-3">
      {" "}
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
            reset(CREATE_DEFAULTS);
            setIsCreateOpen(true);
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
                      title={item.domain_name || ""}
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
      {/* ✅ Правило №20: Модалка с key и проверкой на null */}
      {(isCreateOpen || (editingDoctype && editModalOpen)) && (
        <Dialog
          open={isCreateOpen || editModalOpen}
          onOpenChange={(open) => {
            if (!open) {
              setIsCreateOpen(false);
              setEditModalOpen(false);
              setEditingDoctype(null);
              reset(CREATE_DEFAULTS);
            }
          }}
        >
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>
                {editingDoctype ? "Редактирование" : "Создание"} типа документа
              </DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">
                    Код (системное имя)
                  </label>
                  <Input
                    {...control.register("doctype")}
                    disabled={!!editingDoctype}
                    placeholder="например, invoices"
                  />
                  {errors.doctype && (
                    <p className="text-xs text-destructive">
                      {errors.doctype.message}
                    </p>
                  )}
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Название</label>
                  <Input
                    {...control.register("doctype_name")}
                    placeholder="например, Счета-фактуры"
                  />
                  {errors.doctype_name && (
                    <p className="text-xs text-destructive">
                      {errors.doctype_name.message}
                    </p>
                  )}
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4 items-end">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Домен</label>
                  <Controller
                    name="domain_id"
                    control={control}
                    render={({ field }) => (
                      <ReferenceSelect
                        // ✅ АДАПТЕР: Преобразуем ApiResponse в формат, ожидаемый ReferenceSelect
                        fetchFn={async (params) => {
                          const response = await getDomainsDomainsGet(params);
                          // Распаковываем ApiResponse -> { items, total }
                          // (используем response?.data, так как Orval оборачивает ответ в поле data)
                          return {
                            items: response?.data?.items ?? [],
                            total: response?.data?.total ?? 0,
                          };
                        }}
                        queryKey={["domains"]}
                        value={field.value}
                        onValueChange={field.onChange}
                        placeholder="Выберите домен..."
                        limit={50}
                        heading="Домены"
                        columns={[
                          { column: "description", label: "Описание" },
                          // { column: "name", label: "Название полное" },
                        ]}
                      />
                    )}
                  />
                  {errors.domain_id && (
                    <p className="text-xs text-destructive">
                      {errors.domain_id.message}
                    </p>
                  )}
                </div>
                {/* 🎨 Красивый переключатель статуса (Правило №34) */}
                <div className="mt-0">
                  <Controller
                    name="is_active"
                    control={control}
                    render={({ field }) => (
                      <>
                        <Switch
                          id="is_active"
                          checked={field.value}
                          onCheckedChange={field.onChange}
                        />
                        <Label
                          htmlFor="is_active"
                          className={`flex items-center gap-2 cursor-pointer font-medium transition-colors ${
                            field.value
                              ? "text-green-600 dark:text-green-400"
                              : "text-red-500 dark:text-red-400"
                          }`}
                        >
                          {field.value ? (
                            <>
                              <CheckCircle2 className="h-4 w-4" />
                              Активен
                            </>
                          ) : (
                            <>
                              <PauseCircle className="h-4 w-4" />
                              Неактивен
                            </>
                          )}
                        </Label>
                      </>
                    )}
                  />
                </div>
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Описание</label>
                <Input {...control.register("description")} />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">
                  Доступно организациям (Tenant)
                </label>
                <Controller
                  name="tenant_ids"
                  control={control}
                  render={({ field }) => (
                    <TenantMultiSelect
                      value={field.value ?? []}
                      onChange={field.onChange}
                    />
                  )}
                />
              </div>
              <DialogFooter>
                <Button type="submit" disabled={isSubmitting}>
                  {isSubmitting ? "Сохранение..." : "Сохранить"}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      )}
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
