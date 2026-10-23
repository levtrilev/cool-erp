import { useState, useEffect, useMemo } from "react";
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
import { useToast } from "@/components/ui/use-toast";
import { Trash2, Search, Loader2, Shield, User, Plus, Building2, X } from "lucide-react";
// ✅ НОВОЕ: эндпоинт из модуля users с поддержкой tenant_id
import {
  useReadUsersUsersGet,
  useDeleteUserUsersUserIdDelete,
  readUsersUsersGet,
} from "@/api/generated/users/users";
// ✅ НОВОЕ: текущий пользователь и справочник организаций
import { useGetUserAuthUserGet } from "@/api/generated/authentication/authentication";
import { readTenantsTenantsGet } from "@/api/generated/tenants/tenants";
import { ReferenceSelect, type ReferenceItem } from "@/lib/reusable/ReferenceSelect";
import { EditUserModal } from "@/core/users/EditUserModal";
import { CreateUserModal } from "@/core/users/CreateUserModal";
// ✅ НОВОЕ: общий тип UserResponseSchema
import type { UserResponseSchema } from "@/api/generated/fastAPI.schemas";
import { useQueryClient } from "@tanstack/react-query";
import { Label } from "@/components/ui/label";

// type UserResponseSchema = z.infer<
//   typeof readUsersAuthGetResponse
// >["items"][number];

export const AdminUsersPage = () => {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [limit] = useState(10);

  // ✅ РАЗДЕЛЯЕМ СОСТОЯНИЯ:
  const [searchInput, setSearchInput] = useState(""); // То, что пользователь печатает прямо сейчас
  const [search, setSearch] = useState(""); // То, что реально отправляется в API

  const [deleteUserId, setDeleteUserId] = useState<string | null>(null);

  const [editUser, setEditUser] = useState<UserResponseSchema | null>(null);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [createModalOpen, setCreateModalOpen] = useState(false);

  const [highlightedUserId, setHighlightedUserId] = useState<string | null>(
    null,
  );
  // ✅ НОВОЕ: Определяем права текущего пользователя
  const { data: currentUserData } = useGetUserAuthUserGet();
  const isSuperadmin = currentUserData?.data?.is_superadmin === true;
  const currentTenantId = currentUserData?.data?.tenant_id || "";

  // ✅ НОВОЕ: Фильтр по организации (только для суперадмина)
  // Пустая строка = все организации
  const [selectedTenantId, setSelectedTenantId] = useState<string>("");
  // ✅ НОВОЕ: Справочник организаций для отображения имени в фильтре
  const [tenants, setTenants] = useState<ReferenceItem[]>([]);
  useEffect(() => {
    if (isSuperadmin) {
      readTenantsTenantsGet({ limit: 1000, skip: 0 }).then((response) => {
        const items: ReferenceItem[] = (response?.items ?? []).map((t) => ({
          id: t.id,
          name: t.name,
        }));
        setTenants(items);
      });
    }
  }, [isSuperadmin]);

  const selectedTenantName = useMemo<string>(() => {
    if (!selectedTenantId) return "";
    return tenants.find((t) => t.id === selectedTenantId)?.name ?? "";
  }, [selectedTenantId, tenants]);

  // ✅ Эффективный tenant_id для запроса
  // - Суперадмин без выбранной организации → все организации
  // - Суперадмин с выбранной организацией → конкретная
  // - Обычный пользователь → всегда своя организация
  const effectiveTenantId: string | undefined = isSuperadmin
    ? (selectedTenantId || undefined)
    : currentTenantId;  

  const skip = (page - 1) * limit;

  // ✅ Запрос через эндпоинт /users/ с поддержкой tenant_id
  const { data, isLoading, isError, refetch } = useReadUsersUsersGet({
    tenant_id: effectiveTenantId,
    skip,
    limit,
    search: search || undefined,
  });

  // ✅ Мутация удаления через модуль users
  const deleteUserMutation = useDeleteUserUsersUserIdDelete();

  useEffect(() => {
    if (highlightedUserId) {
      const timer = setTimeout(() => {
        setHighlightedUserId(null);
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [highlightedUserId]);

  const handleUserUpdated = async (userId: string, userName: string) => {
    const result = await refetch();
    const updatedItems = result.data?.items || [];

    const userExists = updatedItems.some((u) => u.id === userId);

    if (userExists) {
      setHighlightedUserId(userId);
      return;
    }

    try {
      // ✅ Используем readUsersUsersGet с tenant_id
      const allUsersData = await readUsersUsersGet({
        tenant_id: effectiveTenantId,
        limit: 1000,
        skip: 0,
      });

      if (allUsersData?.items) {
        const userIndex = allUsersData.items.findIndex(
          (u: UserResponseSchema) => u.id === userId,
        );

        if (userIndex !== -1) {
          const targetPage = Math.floor(userIndex / limit) + 1;

          toast({
            title: "Пользователь обновлен",
            description: `Запись "${userName}" переместилась на страницу ${targetPage}`,
            action: (
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setPage(targetPage);
                  setTimeout(() => {
                    setHighlightedUserId(userId);
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
        title: "Пользователь обновлен",
        description: "Запись переместилась на другую страницу",
      });
    } catch (error) {
      console.error("Ошибка поиска пользователя:", error);
      toast({
        variant: "destructive",
        title: "Ошибка",
        description: "Не удалось определить новое местоположение записи",
      });
    }
  };

  const handleUserCreated = async (newId: string) => {
    // ✅ Инвалидируем кэш списка пользователей — это заставит его перезапроситься
    await queryClient.invalidateQueries({ queryKey: ["users"] });
    
    // ✅ Также перезапрашиваем текущую страницу списка
    await refetch();

    // ✅ Используем readUsersUsersGet с tenant_id
    const allUsersData = await readUsersUsersGet({
      tenant_id: effectiveTenantId,
      limit: 1000,
      skip: 0,
    });

    if (!allUsersData?.items) {
      console.log("❌ Нет items в allUsersData.data");
      toast({
        title: "Создано",
        description: "Запись успешно добавлена в систему",
      });
      return;
    }

    const itemIndex = allUsersData.items.findIndex(
      (u: UserResponseSchema) => u.id === newId,
    );

    if (itemIndex === -1) {
      toast({
        title: "Создано",
        description: "Запись успешно добавлена в систему",
      });
      return;
    }

    const targetPage = Math.floor(itemIndex / limit) + 1;
    console.log("🔍 Целевая страница:", targetPage);

    if (targetPage === page) {
      setHighlightedUserId(newId);

      toast({
        title: "Пользователь создан",
        description: "Запись добавлена и выделена в списке",
      });

      setTimeout(() => {
        setHighlightedUserId(null);
      }, 3000);

      return;
    }

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
              setHighlightedUserId(newId);
              setTimeout(() => {
                setHighlightedUserId(null);
              }, 3000);
            }, 500);
          }}
        >
          Перейти
        </Button>
      ),
    });
  };

  const handleDelete = async (userId: string) => {
    deleteUserMutation.mutate(
      { userId },
      {
        onSuccess: async () => {
          toast({
            title: "Пользователь удален",
            description: "Запись успешно удалена из базы данных",
          });
          await refetch();
          setDeleteUserId(null);
        },
        onError: () => {
          toast({
            variant: "destructive",
            title: "Ошибка",
            description: "Не удалось удалить пользователя",
          });
        },
      },
    );
  };

  const handleEdit = (user: UserResponseSchema) => {
    setEditUser(user);
    setEditModalOpen(true);
  };

  // ✅ ОБНОВЛЕННАЯ ЛОГИКА ПОИСКА
  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault(); // Предотвращаем перезагрузку страницы
    setSearch(searchInput); // Синхронизируем запрос с введенным текстом
    setPage(1); // Сбрасываем на первую страницу результатов
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="text-center text-destructive py-8">
        Не удалось загрузить список пользователей
      </div>
    );
  }

  const users = data.items || [];
  const total = data.total || 0;
  const totalPages = Math.ceil(total / limit);

  return (
    <div className="container mx-auto px-4 py-3">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-2 mb-2">
        <div>
          <h1 className="text-xl font-bold flex items-center gap-2">
            <User className="h-5 w-5 text-primary" />
            Управление пользователями
          </h1>
          <p className="text-xs text-muted-foreground mt-0.5">Всего: {total}</p>
        </div>

        <div className="flex gap-2 w-full md:w-auto">
          <Button onClick={() => setCreateModalOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Создать
          </Button>

          {/* ✅ Оборачиваем в form для перехвата нажатия Enter */}
          <form
            onSubmit={handleSearch}
            className="flex gap-2 flex-1 md:flex-initial"
          >
            <Input
              placeholder="Поиск по имени или email..."
              value={searchInput} // Используем локальный стейт
              onChange={(e) => setSearchInput(e.target.value)} // Обновляем только локально, без запроса к API
              className="w-full md:w-64"
            />
            <Button type="submit" variant="secondary">
              <Search className="h-4 w-4 mr-2" />
              Найти
            </Button>
          </form>
        </div>
      </div>

      {/* ✅ Фильтр по организации (только для суперадмина) */}
      {isSuperadmin && (
        <div className="flex items-center gap-2 mb-3 p-2 rounded-md border bg-muted/30">
          <Building2 className="h-4 w-4 text-muted-foreground shrink-0" />
          <Label className="text-sm font-medium whitespace-nowrap shrink-0">
            Организация:
          </Label>
          <div className="flex-1 max-w-md">
            <ReferenceSelect
              fetchFn={async (params) => {
                const response = await readTenantsTenantsGet({
                  skip: params.skip,
                  limit: params.limit,
                  search: params.search,
                });
                const items: ReferenceItem[] = (response?.items ?? []).map((t) => ({
                  id: t.id,
                  name: t.name,
                }));
                return { items, total: response?.total ?? 0 };
              }}
              queryKey={["tenants-for-user-filter"]}
              value={selectedTenantId}
              onValueChange={(value) => {
                setSelectedTenantId(value);
                setPage(1); // ✅ Сброс пагинации при смене фильтра
              }}
              placeholder="Все организации"
              selectedLabel={selectedTenantName || "Все организации"}
              heading="Выберите организацию"
            />
          </div>
          {selectedTenantId && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => { setSelectedTenantId(""); setPage(1); }}
              className="shrink-0 text-muted-foreground"
            >
              <X className="h-4 w-4 mr-1" /> Сбросить
            </Button>
          )}
        </div>
      )}

      <div className="rounded-md border bg-card">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="h-10 py-2">Имя</TableHead>
              <TableHead className="h-10 py-2">Email</TableHead>
              <TableHead className="h-10 py-2">Организация</TableHead>
              <TableHead className="h-10 py-2">Роль</TableHead>
              <TableHead className="h-10 py-2 text-right">Действия</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {users.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={4}
                  className="text-center text-muted-foreground py-8"
                >
                  Пользователи не найдены
                </TableCell>
              </TableRow>
            ) : (
              users.map((user) => (
                <TableRow
                  key={user.id}
                  className={
                    highlightedUserId === user.id
                      ? "bg-yellow-100 dark:bg-yellow-900/30 transition-colors duration-300"
                      : ""
                  }
                >
                  <TableCell className="py-1">
                    <button
                      type="button"
                      onClick={() => handleEdit(user)}
                      className="text-blue-600 hover:text-blue-800 hover:underline cursor-pointer text-left font-medium"
                    >
                      {user.name}
                    </button>
                  </TableCell>
                  <TableCell className="py-1">{user.email}</TableCell>
                  <TableCell className="py-1">{user.tenant_name}</TableCell>
                  <TableCell className="py-1">
                    <div className="flex items-center gap-2">
                      {user.is_superadmin ? (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                          <Shield className="h-3 w-3 mr-1" /> Супер-админ
                        </span>
                      ) : user.is_admin ? (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                          <Shield className="h-3 w-3 mr-1" /> Админ
                        </span>
                      ) : (
                        <span className="text-muted-foreground text-sm">
                          Пользователь
                        </span>
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="py-1 text-right">
                    <div className="flex justify-end gap-2">
                      <AlertDialog
                        open={deleteUserId === user.id}
                        onOpenChange={(open) => !open && setDeleteUserId(null)}
                      >
                        <AlertDialogTrigger asChild>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="text-destructive hover:text-destructive hover:bg-destructive/10"
                            onClick={() => setDeleteUserId(user.id)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogHeader>
                            <AlertDialogTitle>Вы уверены?</AlertDialogTitle>
                            <AlertDialogDescription>
                              Это действие нельзя отменить. Пользователь{" "}
                              <strong>{user.name}</strong> будет безвозвратно
                              удален из системы.
                            </AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel>Отмена</AlertDialogCancel>
                            <AlertDialogAction
                              onClick={() => handleDelete(user.id)}
                              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                              disabled={deleteUserMutation.isPending}
                            >
                              {deleteUserMutation.isPending
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
      {editUser && (
        <EditUserModal
          key={editUser.id}
          open={editModalOpen}
          onOpenChange={setEditModalOpen}
          user={editUser}
          onUserUpdated={handleUserUpdated}
        />
      )}
      <CreateUserModal
        open={createModalOpen}
        onOpenChange={setCreateModalOpen}
        onUserCreated={handleUserCreated}
      />
    </div>
  );
};
