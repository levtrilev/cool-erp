import { useState, useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Plus, Search, Trash2, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
import { useToast } from "@/components/ui/use-toast";
import { useResizableColumns } from "@/components/hooks/useResizableColumns";

// ✅ Правило №9 и №10: Orval хуки и типы
import { 
  useGetDomainsDomainsGet, 
  useCreateDomainDomainsPost, 
  useUpdateDomainDomainsDomainIdPut, 
  useDeleteDomainDomainsDomainIdDelete 
} from "@/api/generated/domains/domains";
import { getDomainsDomainsGet } from "@/api/generated/domains/domains";
import type { DomainResponseSchema, DomainCreateSchema, DomainUpdateSchema } from "@/api/generated/fastAPI.schemas";

const domainSchema = z.object({
  name: z.string().min(2, "Минимум 2 символа"),
  description: z.string().optional(),
});

type DomainFormData = z.infer<typeof domainSchema>;

export const DomainsPage = () => {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const limit = 10;

  // ✅ Правило №22: Структура состояний
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editingDomain, setEditingDomain] = useState<DomainResponseSchema | null>(null);
  const [deleteDomainId, setDeleteDomainId] = useState<string | null>(null);
  const [highlightedDomainId, setHighlightedDomainId] = useState<string | null>(null);

  // ✅ Правило №29: Изменяемые колонки
  const columns = [
    { id: "name", initialWidth: 300, minWidth: 200 },
    { id: "description", initialWidth: 400, minWidth: 250 },
    { id: "count", initialWidth: 100, minWidth: 80 },
    { id: "actions", initialWidth: 50, minWidth: 50 },
  ];
  const { widths, handleMouseDown, resetWidths } = useResizableColumns(columns, "domains-table-widths");

  // ✅ Правило №9: Orval хуки
  const { data, isLoading, refetch } = useGetDomainsDomainsGet({
    skip: (page - 1) * limit, limit, search: search || undefined
  });
  const createMutation = useCreateDomainDomainsPost();
  const updateMutation = useUpdateDomainDomainsDomainIdPut();
  const deleteMutation = useDeleteDomainDomainsDomainIdDelete();

  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<DomainFormData>({
    resolver: zodResolver(domainSchema),
    defaultValues: { name: "", description: "" }
  });

  // ✅ Правило №18 и №23: Умная навигация и подсветка
  const handleSaved = async (id: string) => {
    await refetch();
    const currentItems = data?.data?.items || [];
    if (currentItems.some((item) => item.id === id)) {
      setHighlightedDomainId(id);
      setTimeout(() => setHighlightedDomainId(null), 3000);
      toast({ title: "Успешно сохранено" });
    } else {
      const fullList = await getDomainsDomainsGet({ limit: 1000, skip: 0 });
      const foundIndex = (fullList.data?.items || []).findIndex((item) => item.id === id);
      if (foundIndex !== -1) {
        const targetPage = Math.ceil((foundIndex + 1) / limit);
        toast({
          title: "Сохранено",
          description: `На странице ${targetPage}`,
          action: <Button variant="outline" size="sm" onClick={() => setPage(targetPage)}>Перейти</Button>,
        });
      }
    }
  };

  // ✅ Правило №24: invalidateQueries ДО закрытия модалки
  const onSubmit = async (formData: DomainFormData) => {
    try {
      if (editingDomain) {
        await updateMutation.mutateAsync({ domainId: editingDomain.id, data: formData as DomainUpdateSchema });
        await queryClient.invalidateQueries({ queryKey: ["domains"] });
        setEditModalOpen(false);
        setEditingDomain(null);
        await handleSaved(editingDomain.id);
      } else {
        const res = await createMutation.mutateAsync({ data: formData as DomainCreateSchema });
        await queryClient.invalidateQueries({ queryKey: ["domains"] });
        setIsCreateOpen(false);
        await handleSaved(res.data!.id);
      }
      reset();
    } catch (error) {
      toast({ variant: "destructive", title: "Ошибка", description: "Не удалось сохранить домен: " + String(error) });
    }
  };

  // ✅ Правило №25: refetch() после удаления
  const handleDelete = async () => {
    if (!deleteDomainId) return;
    try {
      await deleteMutation.mutateAsync({ domainId: deleteDomainId });
      await refetch();
      setDeleteDomainId(null);
      toast({ title: "Домен удалён" });
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } catch (error: any) {
      toast({ 
        variant: "destructive", 
        title: "Ошибка удаления", 
        description: error.response?.data?.detail || "Не удалось удалить домен" 
      });
    }
  };

  // ✅ Правило №17: Подсветка через useEffect
  useEffect(() => {
    if (highlightedDomainId && data?.data?.items?.some(i => i.id === highlightedDomainId)) {
      const timer = setTimeout(() => setHighlightedDomainId(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [data, highlightedDomainId]);

  const openEdit = (item: DomainResponseSchema) => {
    setEditingDomain(item);
    reset({
      name: item.name,
      description: item.description || "",
    });
    setEditModalOpen(true);
  };

  const items = data?.data?.items || [];

  return (
    <div className="container mx-auto px-4 py-3"> {/* ✅ Правило №11 */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-2 mb-2">
        <div>
          <h1 className="text-xl font-bold">Домены</h1>
          <p className="text-xs text-muted-foreground mt-0.5">Всего: {data?.data?.total || 0}</p>
        </div>
        <Button onClick={() => { reset(); setIsCreateOpen(true); }}>
          <Plus className="mr-2 h-4 w-4" /> Создать домен
        </Button>
      </div>

      {/* ✅ Правило №12: Поиск через form */}
      <form onSubmit={(e) => { e.preventDefault(); setSearch(searchInput); setPage(1); }} className="flex gap-2 mb-2">
        <div className="relative flex-1 max-w-sm">
          <Input value={searchInput} onChange={(e) => setSearchInput(e.target.value)} placeholder="Поиск по названию..." className="pl-9" />
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        </div>
        <Button type="submit" variant="secondary">Найти</Button>
      </form>

      {/* ✅ Правила №13, №14, №29: Таблица */}
      <div className="rounded-md border bg-card">
        <div className="flex justify-end p-2 border-b">
          <Button variant="ghost" size="sm" onClick={resetWidths} className="text-xs">Сбросить ширину</Button>
        </div>
        <Table className="table-fixed w-full">
          <TableHeader>
            <TableRow className="h-10 hover:bg-transparent">
              <TableHead className="relative" style={{ width: widths.name }}>Название<div className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary/20" onMouseDown={(e) => handleMouseDown("name", e)} /></TableHead>
              <TableHead className="relative" style={{ width: widths.description }}>Описание<div className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary/20" onMouseDown={(e) => handleMouseDown("description", e)} /></TableHead>
              <TableHead className="relative" style={{ width: widths.count }}>Типов док.<div className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary/20" onMouseDown={(e) => handleMouseDown("count", e)} /></TableHead>
              <TableHead style={{ width: widths.actions }}></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow><TableCell colSpan={4} className="text-center py-8"><Loader2 className="h-6 w-6 animate-spin mx-auto" /></TableCell></TableRow>
            ) : items.length === 0 ? (
              <TableRow><TableCell colSpan={4} className="text-center text-muted-foreground py-8">Не найдено</TableCell></TableRow>
            ) : (
              items.map((item) => (
                <TableRow key={item.id} className={highlightedDomainId === item.id ? "bg-yellow-100 dark:bg-yellow-900/30 transition-colors duration-300" : ""}>
                  <TableCell className="py-1 align-top overflow-hidden" style={{ width: widths.name }}>
                    <button onClick={() => openEdit(item)} title={item.name} className="block w-full text-left text-blue-600 hover:text-blue-800 hover:underline cursor-pointer font-medium truncate">{item.name}</button>
                  </TableCell>
                  <TableCell className="py-1 align-top overflow-hidden" style={{ width: widths.description }}>
                    <div title={item.description || ""} className="block w-full truncate">{item.description || "—"}</div>
                  </TableCell>
                  <TableCell className="py-1 align-top" style={{ width: widths.count }}>
                    <span className="text-sm font-medium">{item.doctypes_count || 0}</span>
                  </TableCell>
                  <TableCell className="py-1 align-top" style={{ width: widths.actions }}>
                    <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive" onClick={() => setDeleteDomainId(item.id)}><Trash2 className="h-4 w-4" /></Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* ✅ Правило №20: Модалка с проверкой на null */}
      {(isCreateOpen || (editingDomain && editModalOpen)) && (
        <Dialog open={isCreateOpen || editModalOpen} onOpenChange={(open) => {
          if (!open) { setIsCreateOpen(false); setEditModalOpen(false); setEditingDomain(null); reset(); }
        }}>
          <DialogContent className="max-w-lg">
            <DialogHeader><DialogTitle>{editingDomain ? "Редактирование" : "Создание"} домена</DialogTitle></DialogHeader>
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Название</label>
                <Input {...register("name")} />
                {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Описание</label>
                <Input {...register("description")} />
              </div>
              <DialogFooter>
                <Button type="submit" disabled={isSubmitting}>{isSubmitting ? "Сохранение..." : "Сохранить"}</Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      )}

      {/* ✅ Правило №16: AlertDialog для удаления */}
      <AlertDialog open={!!deleteDomainId} onOpenChange={(open) => !open && setDeleteDomainId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Удалить домен?</AlertDialogTitle>
            <AlertDialogDescription>
              Это действие нельзя отменить. Убедитесь, что в домене нет типов документов.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Отмена</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete} disabled={deleteMutation.isPending} className="bg-destructive text-destructive-foreground">
              {deleteMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : "Удалить"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};