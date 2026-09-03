import { useState, useEffect } from "react";
// import { useQueryClient } from "@tanstack/react-query";
import { Plus, Search, Trash2, Building2, Loader2 } from "lucide-react";
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
import { useToast } from "@/components/ui/use-toast";
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { CreateTenantModal } from "./CreateTenantModal";
import { EditTenantModal } from "./EditTenantModal";
import {
  useReadTenantsTenantsGet,
  readTenantsTenantsGet,
  useDeleteTenantTenantsTenantIdDelete,
} from "@/api/generated/tenants/tenants";
import type { TenantResponseSchema } from "@/api/generated/fastAPI.schemas";

export function AdminTenantsPage() {
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [limit] = useState(10);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingTenant, setEditingTenant] =
    useState<TenantResponseSchema | null>(null);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [deleteTenantId, setDeleteTenantId] = useState<string | null>(null);
  const [highlightedTenantId, setHighlightedTenantId] = useState<string | null>(
    null,
  );
  // const queryClient = useQueryClient();
  const { toast } = useToast();

  const skip = (page - 1) * limit;

  // Получение списка тенантов
  const {
    data: tenantsData,
    isLoading,
    isError,
    refetch,
  } = useReadTenantsTenantsGet({
    skip,
    limit,
    search: search || undefined,
  });

  // Удаление тенанта
  const deleteMutation = useDeleteTenantTenantsTenantIdDelete();

  // Автосброс подсветки через 3 секунды
  useEffect(() => {
    if (highlightedTenantId) {
      const timer = setTimeout(() => {
        setHighlightedTenantId(null);
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [highlightedTenantId]);

  // Обработка обновления тенанта (из EditTenantModal)
  const handleTenantUpdated = async (tenantId: string, tenantName: string) => {
    // Сначала обновляем данные
    const result = await refetch();
    const updatedItems = result.data?.items || [];

    // Проверяем, есть ли запись на текущей странице
    const tenantExists = updatedItems.some((t) => t.id === tenantId);

    if (tenantExists) {
      // Запись на текущей странице - подсвечиваем
      setHighlightedTenantId(tenantId);
      toast({
        title: "Организация обновлена",
        description: "Запись обновлена и выделена в списке",
      });
      return;
    }

    // Записи нет на текущей странице - ищем её в полном списке
    try {
      const allTenantsData = await readTenantsTenantsGet({
        limit: 1000,
        skip: 0,
      });

      if (allTenantsData?.items) {
        const tenantIndex = allTenantsData.items.findIndex(
          (t: TenantResponseSchema) => t.id === tenantId,
        );

        if (tenantIndex !== -1) {
          const targetPage = Math.floor(tenantIndex / limit) + 1;
          toast({
            title: "Организация обновлена",
            description: `Запись "${tenantName}" переместилась на страницу ${targetPage}`,
            action: (
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setPage(targetPage);
                  setTimeout(() => {
                    setHighlightedTenantId(tenantId);
                  }, 500);
                }}
              >
                Перейти
              </Button>
            ),
          });
          return;
        }
      }

      toast({
        title: "Организация обновлена",
        description: "Запись переместилась на другую страницу",
      });
    } catch (error) {
      console.error("Ошибка поиска организации:", error);
      toast({
        variant: "destructive",
        title: "Ошибка",
        description: "Не удалось определить новое местоположение записи",
      });
    }
  };
  // const handleTenantUpdated = async (tenantId: string, tenantName: string) => {
  //   const result = await refetch();
  //   const updatedItems = result.data?.items || [];
  //   const tenantExists = updatedItems.some((t) => t.id === tenantId);

  //   if (tenantExists) {
  //     setHighlightedTenantId(tenantId);
  //     return;
  //   }

  //   try {
  //     const allTenantsData = await readTenantsTenantsGet({
  //       limit: 1000,
  //       skip: 0,
  //     });

  //     if (allTenantsData?.items) {
  //       const tenantIndex = allTenantsData.items.findIndex(
  //         (t: TenantResponseSchema) => t.id === tenantId,
  //       );

  //       if (tenantIndex !== -1) {
  //         const targetPage = Math.floor(tenantIndex / limit) + 1;
  //         toast({
  //           title: "Организация обновлена",
  //           description: `Запись "${tenantName}" переместилась на страницу ${targetPage}`,
  //           action: (
  //             <Button
  //               variant="outline"
  //               size="sm"
  //               onClick={() => {
  //                 setPage(targetPage);
  //                 setTimeout(() => {
  //                   setHighlightedTenantId(tenantId);
  //                 }, 500);
  //               }}
  //             >
  //               Перейти
  //             </Button>
  //           ),
  //         });
  //         return;
  //       }
  //     }

  //     toast({
  //       title: "Организация обновлена",
  //       description: "Запись переместилась на другую страницу",
  //     });
  //   } catch (error) {
  //     console.error("Ошибка поиска организации:", error);
  //     toast({
  //       variant: "destructive",
  //       title: "Ошибка",
  //       description: "Не удалось определить новое местоположение записи",
  //     });
  //   }
  // };

  // Обработка создания тенанта (из CreateTenantModal)
  const handleTenantCreated = async (newId: string) => {
    // Сначала обновляем данные текущей страницы
    const result = await refetch();
    const currentItems = result.data?.items || [];

    // Проверяем, есть ли новая запись на текущей странице
    const tenantExists = currentItems.some((t) => t.id === newId);

    if (tenantExists) {
      // Запись на текущей странице - подсвечиваем
      setHighlightedTenantId(newId);
      toast({
        title: "Создано",
        description: "Запись добавлена и выделена в списке",
      });
      return;
    }

    // Записи нет на текущей странице - ищем её в полном списке
    try {
      const allTenantsData = await readTenantsTenantsGet({
        limit: 1000,
        skip: 0,
      });

      if (allTenantsData?.items) {
        const itemIndex = allTenantsData.items.findIndex(
          (t: TenantResponseSchema) => t.id === newId,
        );

        if (itemIndex !== -1) {
          const targetPage = Math.floor(itemIndex / limit) + 1;
          toast({
            title: "Создано",
            description: `Запись переместилась на страницу ${targetPage}`,
            action: (
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setPage(targetPage);
                  setTimeout(() => {
                    setHighlightedTenantId(newId);
                  }, 500);
                }}
              >
                Перейти
              </Button>
            ),
          });
          return;
        }
      }

      toast({
        title: "Создано",
        description: "Запись успешно добавлена в систему",
      });
    } catch (error) {
      console.error("Ошибка поиска организации:", error);
      toast({
        variant: "destructive",
        title: "Ошибка",
        description: "Не удалось определить местоположение записи",
      });
    }
  };

  // const handleTenantCreated = async (newId: string) => {
  //   const allTenantsData = await readTenantsTenantsGet({
  //     limit: 1000,
  //     skip: 0,
  //   });

  //   if (!allTenantsData?.items) {
  //     toast({
  //       title: "Создано",
  //       description: "Запись успешно добавлена в систему",
  //     });
  //     return;
  //   }

  //   const itemIndex = allTenantsData.items.findIndex(
  //     (t: TenantResponseSchema) => t.id === newId,
  //   );

  //   if (itemIndex === -1) {
  //     toast({
  //       title: "Создано",
  //       description: "Запись успешно добавлена в систему",
  //     });
  //     return;
  //   }

  //   const targetPage = Math.floor(itemIndex / limit) + 1;

  //   if (targetPage === page) {
  //     setHighlightedTenantId(newId);
  //     toast({
  //       title: "Создано",
  //       description: "Запись добавлена и выделена в списке",
  //     });
  //     setTimeout(() => {
  //       setHighlightedTenantId(null);
  //     }, 3000);
  //     return;
  //   }

  //   toast({
  //     title: "Создано",
  //     description: `Запись переместилась на страницу ${targetPage}`,
  //     action: (
  //       <Button
  //         variant="outline"
  //         size="sm"
  //         onClick={() => {
  //           setPage(targetPage);
  //           setTimeout(() => {
  //             setHighlightedTenantId(newId);
  //             setTimeout(() => {
  //               setHighlightedTenantId(null);
  //             }, 3000);
  //           }, 500);
  //         }}
  //       >
  //         Перейти
  //       </Button>
  //     ),
  //   });
  // };

  // Удаление
  const handleDelete = (tenantId: string) => {
    deleteMutation.mutate(
      { tenantId },
      {
        onSuccess: async () => {
          toast({
            title: "Организация удалена",
            description: "Запись успешно удалена из базы данных",
          });
          await refetch();
          setDeleteTenantId(null);
        },
        onError: () => {
          toast({
            variant: "destructive",
            title: "Ошибка",
            description: "Не удалось удалить организацию",
          });
        },
      },
    );
  };

  const handleEdit = (tenant: TenantResponseSchema) => {
    setEditingTenant(tenant);
    setEditModalOpen(true);
  };

  // Поиск через form
  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setSearch(searchInput);
    setPage(1);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (isError || !tenantsData) {
    return (
      <div className="text-center text-destructive py-8">
        Не удалось загрузить список организаций
      </div>
    );
  }

  const tenants = tenantsData.items || [];
  const total = tenantsData.total || 0;
  const totalPages = Math.ceil(total / limit);

  return (
    <div className="container mx-auto px-4 py-3">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-2 mb-2">
        <div>
          <h1 className="text-xl font-bold flex items-center gap-2">
            <Building2 className="h-5 w-5 text-primary" />
            Организации
          </h1>
          <p className="text-xs text-muted-foreground mt-0.5">Всего: {total}</p>
        </div>
        <div className="flex gap-2 w-full md:w-auto">
          <Button onClick={() => setIsCreateOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Создать
          </Button>
          <form
            onSubmit={handleSearch}
            className="flex gap-2 flex-1 md:flex-initial"
          >
            <Input
              placeholder="Поиск по названию..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              className="w-full md:w-64"
            />
            <Button type="submit" variant="secondary">
              <Search className="h-4 w-4 mr-2" />
              Найти
            </Button>
          </form>
        </div>
      </div>

      <div className="rounded-md border bg-card">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="h-10 py-2">Название</TableHead>
              <TableHead className="h-10 py-2">Описание</TableHead>
              <TableHead className="h-10 py-2">Статус</TableHead>
              <TableHead className="h-10 py-2 text-right">Действия</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {tenants.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={4}
                  className="text-center text-muted-foreground py-8"
                >
                  Организации не найдены
                </TableCell>
              </TableRow>
            ) : (
              tenants.map((tenant) => (
                <TableRow
                  key={tenant.id}
                  className={
                    highlightedTenantId === tenant.id
                      ? "bg-yellow-100 dark:bg-yellow-900/30 transition-colors duration-300"
                      : ""
                  }
                >
                  <TableCell className="py-1">
                    <button
                      type="button"
                      onClick={() => handleEdit(tenant)}
                      className="text-blue-600 hover:text-blue-800 hover:underline cursor-pointer text-left font-medium"
                    >
                      {tenant.name}
                    </button>
                  </TableCell>
                  <TableCell className="py-1">
                    {tenant.description || "—"}
                  </TableCell>
                  <TableCell className="py-1">
                    <span
                      className={`px-2 py-1 rounded-full text-xs ${
                        tenant.active
                          ? "bg-green-100 text-green-800"
                          : "bg-gray-100 text-gray-800"
                      }`}
                    >
                      {tenant.active ? "Активна" : "Неактивна"}
                    </span>
                  </TableCell>
                  <TableCell className="py-1 text-right">
                    <div className="flex justify-end gap-2">
                      <AlertDialog
                        open={deleteTenantId === tenant.id}
                        onOpenChange={(open) =>
                          !open && setDeleteTenantId(null)
                        }
                      >
                        <AlertDialogTrigger asChild>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="text-destructive hover:text-destructive hover:bg-destructive/10"
                            onClick={() => setDeleteTenantId(tenant.id)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogHeader>
                            <AlertDialogTitle>Вы уверены?</AlertDialogTitle>
                            <AlertDialogDescription>
                              Это действие нельзя отменить. Организация{" "}
                              <strong>{tenant.name}</strong> будет безвозвратно
                              удалена из системы.
                            </AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel>Отмена</AlertDialogCancel>
                            <AlertDialogAction
                              onClick={() => handleDelete(tenant.id)}
                              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                              disabled={deleteMutation.isPending}
                            >
                              {deleteMutation.isPending
                                ? "Удаление..."
                                : "Удалить"}
                            </AlertDialogAction>
                          </AlertDialogFooter>
                        </AlertDialogContent>
                      </AlertDialog>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {totalPages > 1 && (
        <div className="mt-6 flex justify-center">
          <Pagination>
            <PaginationContent>
              <PaginationItem>
                <PaginationPrevious
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  className={
                    page === 1
                      ? "pointer-events-none opacity-50"
                      : "cursor-pointer"
                  }
                />
              </PaginationItem>
              {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                let pageNum = i + 1;
                if (totalPages > 5 && page > 3) {
                  pageNum = page - 2 + i;
                }
                if (pageNum > totalPages) return null;
                return (
                  <PaginationItem key={pageNum}>
                    <PaginationLink
                      isActive={page === pageNum}
                      onClick={() => setPage(pageNum)}
                      className="cursor-pointer"
                    >
                      {pageNum}
                    </PaginationLink>
                  </PaginationItem>
                );
              })}
              <PaginationItem>
                <PaginationNext
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  className={
                    page === totalPages
                      ? "pointer-events-none opacity-50"
                      : "cursor-pointer"
                  }
                />
              </PaginationItem>
            </PaginationContent>
          </Pagination>
        </div>
      )}

      <CreateTenantModal
        open={isCreateOpen}
        onOpenChange={setIsCreateOpen}
        onTenantCreated={handleTenantCreated}
      />
      {editingTenant && (
        <EditTenantModal
          key={editingTenant.id}
          open={editModalOpen}
          onOpenChange={setEditModalOpen}
          tenant={editingTenant}
          onTenantUpdated={handleTenantUpdated}
        />
      )}
    </div>
  );
}
