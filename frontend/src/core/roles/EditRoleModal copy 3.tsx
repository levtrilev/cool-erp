import { useState, useMemo, useEffect, useRef } from "react";
import { useForm, Controller, type FieldErrors } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useQueryClient } from "@tanstack/react-query";
import { Loader2, Check, Building2 } from "lucide-react";
import { useToast } from "@/components/ui/use-toast";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useSaveRoleRolesSavePost } from "@/api/generated/roles/roles";
import {
  getSectionsSectionsGet,
  useGetSectionsSectionsGet,
} from "@/api/generated/sections/sections";
import { useReadUsersUsersGet } from "@/api/generated/users/users";
import { useGetUserAuthUserGet } from "@/api/generated/authentication/authentication";
import { readTenantsTenantsGet } from "@/api/generated/tenants/tenants";
import type { RoleResponseSchema } from "@/api/generated/fastAPI.schemas";
import { PermissionsTab, type PermissionDraft } from "./PermissionsTab";
import { UsersTab, type UserDraft } from "./UsersTab";
import { MultiSelectChips } from "@/lib/reusable/MultiSelectChips";
import { ReferenceSelect } from "@/lib/reusable/ReferenceSelect";

// ✅ Правило №20: Константа для сброса формы
const CREATE_DEFAULTS: RoleFormData = {
  name: "",
  description: "",
};

const roleSchema = z.object({
  name: z.string().min(1, "Название обязательно"),
  description: z.string().optional(),
});

type RoleFormData = z.infer<typeof roleSchema>;

interface EditRoleModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  role?: RoleResponseSchema | null;
  onRoleSaved: (id: string, name: string) => void;
}

// ✅ Правило №36: Кастомный тип для пользователя с role_ids
interface UserWithRoles {
  id: string;
  name: string;
  email?: string | null;
  role_ids?: string[];
}

export function EditRoleModal({
  open,
  onOpenChange,
  role,
  onRoleSaved,
}: EditRoleModalProps) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const { data: userData } = useGetUserAuthUserGet();
  const currentTenantId = userData?.data?.tenant_id;
  const isSuperadmin = userData?.data?.is_superadmin === true;
  const isEdit = !!role;

  const { control, handleSubmit, reset } = useForm<RoleFormData>({
    resolver: zodResolver(roleSchema),
    defaultValues: CREATE_DEFAULTS,
  });

  // ✅ Правило №37: Паттерн с sessionKey для гарантированного перемонта при открытии
  const [sessionKey, setSessionKey] = useState(0);

  const handleOpenChange = (newOpen: boolean) => {
    if (newOpen && !open) {
      setSessionKey((prev) => prev + 1);
    }
    if (!newOpen) {
      reset(CREATE_DEFAULTS); // ✅ Правило №20
    }
    onOpenChange(newOpen);
  };

  // ==========================================
  // ✅ ПОЛЕ ПРЕДПРИЯТИЕ (ОРГАНИЗАЦИЯ) - СОСТОЯНИЕ
  // ==========================================
  // ✅ Правило №37: Инициализация напрямую из пропсов.
  // Благодаря key={role?.id || 'new'} на <form>, компонент пересоздается при смене role,
  // и useState получает актуальное значение БЕЗ вызова setState в useEffect.
  const [selectedTenantId, setSelectedTenantId] = useState<string>(
    role?.tenant_id || currentTenantId || "",
  );
  const [selectedTenantName] = useState<string>(role?.tenant_name || "");

  // Разрешена ли смена организации (только суперадмин при редактировании)
  const canChangeTenant = isEdit && isSuperadmin;

  // ✅ Проверка наличия связей перед сменой организации
  // ✅ Исправлено: принимает только (value: string), как требует ReferenceSelect
  const handleTenantChange = (newTenantId: string) => {
    if (newTenantId === selectedTenantId) return;

    // Проверяем наличие связей в ИСХОДНЫХ данных роли (из БД)
    const hasSections = (role?.section_ids?.length ?? 0) > 0;
    const hasPermissions = (role?.permissions?.length ?? 0) > 0;
    const hasUsers = initialUserIds.length > 0;

    if (hasSections || hasPermissions || hasUsers) {
      const assigned: string[] = [];
      if (hasSections) assigned.push("Разделы");
      if (hasPermissions) assigned.push("Полномочия");
      if (hasUsers) assigned.push("Пользователи");

      toast({
        variant: "destructive",
        title: "Нельзя изменить организацию",
        description: `Для роли "${role?.name}" уже назначены: ${assigned.join(", ")}. Сначала удалите все назначения.`,
      });
      return; // ❌ Отменяем изменение
    }

    // ✅ Связей нет — разрешаем смену
    setSelectedTenantId(newTenantId);
    // Примечание: мы не обновляем selectedTenantName здесь, так как ReferenceSelect
    // передаёт только ID. Название корректно отобразится после сохранения и перезагрузки.

    toast({
      title: "Организация изменена",
      description: "Роль будет сохранена для новой организации.",
    });
  };

  const hasTenantChanges = useMemo(
    () => canChangeTenant && selectedTenantId !== (role?.tenant_id || ""),
    [canChangeTenant, selectedTenantId, role?.tenant_id],
  );

  // ==========================================
  // ДАННЫЕ ПОЛЬЗОВАТЕЛЕЙ (НЕ ТРОНУТО)
  // ==========================================
  const { data: usersData, isLoading: isUsersLoading } = useReadUsersUsersGet({
    tenant_id: selectedTenantId, // ✅ Используем выбранную организацию
    limit: 1000,
    skip: 0,
  });

  // ✅ Правило №36: Безопасное приведение типа для role_ids
  const allUsers = useMemo(() => {
    return (usersData?.items ?? []).map((u) => ({
      id: u.id,
      name: u.name,
      email: u.email,
      role_ids: (u as unknown as UserWithRoles).role_ids || [],
    }));
  }, [usersData]);

  // ✅ Выносим roleId в примитивную переменную (Правило №37 + exhaustive-deps)
  const roleId = role?.id;

  // ✅ Инициализация initialUserIds из role_ids пользователей
  // eslint-disable-next-line react-hooks/preserve-manual-memoization
  const initialUserIds = useMemo(() => {
    if (!roleId || allUsers.length === 0) return [];
    return allUsers
      .filter((u) => u.role_ids?.includes(roleId))
      .map((u) => u.id);
  }, [roleId, allUsers]);

  // ✅ Вычисляем исходный черновик пользователей
  const initialUsersDraft: UserDraft[] = useMemo(() => {
    return allUsers
      .filter((u) => initialUserIds.includes(u.id))
      .map((u) => ({
        id: u.id,
        name: u.name,
        email: u.email || undefined,
        markedForDeletion: false,
      }));
  }, [allUsers, initialUserIds]);

  // ✅ ИСПРАВЛЕНИЕ F5: Состояние черновика начинается пустым
  const [usersDraft, setUsersDraft] = useState<UserDraft[]>([]);
  const lastInitializedRoleId = useRef<string | null>(null);

  // ✅ Синхронизация черновика ТОЛЬКО когда данные гарантированно загружены
  useEffect(() => {
    if (open) {
      if (roleId) {
        if (!isUsersLoading && usersData) {
          if (lastInitializedRoleId.current !== roleId) {
            setUsersDraft(initialUsersDraft);
            lastInitializedRoleId.current = roleId;
          }
        }
      } else {
        // Режим создания новой роли
        // eslint-disable-next-line react-hooks/set-state-in-effect
        setUsersDraft([]);
        lastInitializedRoleId.current = null;
      }
    } else {
      // Закрытие модалки
      setUsersDraft([]);
      lastInitializedRoleId.current = null;
    }
  }, [open, roleId, initialUsersDraft, isUsersLoading, usersData]);

  // ✅ selectedUserIds вычисляется из usersDraft (фильтрует помеченных на удаление)
  const selectedUserIds = useMemo(() => {
    return usersDraft.filter((u) => !u.markedForDeletion).map((u) => u.id);
  }, [usersDraft]);

  // ==========================================
  // ДАННЫЕ РАЗДЕЛОВ (НЕ ТРОНУТО)
  // ==========================================
  // ✅ Правило №37: Инициализация напрямую из пропсов
  const [selectedSectionIds, setSelectedSectionIds] = useState<string[]>(
    role?.section_ids || [],
  );

  const { data: sectionsData } = useGetSectionsSectionsGet({
    limit: 1000,
    skip: 0,
  });

  const sections = useMemo(
    () => sectionsData?.data?.items ?? [],
    [sectionsData],
  );

  // ==========================================
  // ДАННЫЕ ПОЛНОМОЧИЙ (НЕ ТРОНУТО)
  // ==========================================
  const initialPerms: PermissionDraft[] = role?.permissions
    ? role.permissions.map((p) => ({
        id: p.id,
        doctype: p.doctype,
        doctype_name: p.doctype_name ?? undefined,
        role_name: p.role_name ?? undefined,
        tenant_name: p.tenant_name ?? undefined,
        full_access: p.full_access ?? false,
        author: p.author ?? false,
        reader: p.reader ?? false,
        editor: p.editor ?? false,
        can_delete: p.can_delete ?? false,
        access_by_tags: p.access_by_tags ?? false,
      }))
    : [];

  const [permissions, setPermissions] =
    useState<PermissionDraft[]>(initialPerms);
  const [initialPermissionsSnapshot] = useState<string>(
    JSON.stringify(initialPerms),
  );

  // ==========================================
  // ИНДИКАТОРЫ ИЗМЕНЕНИЙ (НЕ ТРОНУТО)
  // ==========================================
  const hasPermissionChanges = useMemo(() => {
    return JSON.stringify(permissions) !== initialPermissionsSnapshot;
  }, [permissions, initialPermissionsSnapshot]);

  // ✅ Обёртываем в useMemo для стабильной ссылки (exhaustive-deps)
  const initialSectionIds = useMemo(
    () => role?.section_ids || [],
    [role?.section_ids],
  );

  const hasSectionChanges = useMemo(() => {
    const initial = initialSectionIds.slice().sort();
    const current = selectedSectionIds.slice().sort();
    return JSON.stringify(initial) !== JSON.stringify(current);
  }, [initialSectionIds, selectedSectionIds]);

  const hasUserChanges = useMemo(() => {
    const initial = initialUserIds.slice().sort();
    const current = selectedUserIds.slice().sort();
    return JSON.stringify(initial) !== JSON.stringify(current);
  }, [initialUserIds, selectedUserIds]);

  // ==========================================
  // ОБРАБОТЧИКИ (ОБНОВЛЕН ТОЛЬКО PAYLOAD)
  // ==========================================
  const saveMutation = useSaveRoleRolesSavePost();

  const onSubmit = async (data: RoleFormData) => {
    if (!selectedTenantId) {
      toast({
        variant: "destructive",
        title: "Ошибка",
        description: "Не выбрана организация для роли",
      });
      return;
    }

    const payload = {
      name: data.name,
      description: data.description || "",
      tenant_id: selectedTenantId, // ✅ Используем выбранную организацию
      section_ids: selectedSectionIds,
      section_names: sections
        .filter((s) => selectedSectionIds.includes(s.id))
        .map((s) => s.name),
      permissions: permissions
        .filter((p) => !p.markedForDeletion)
        .map((p) => ({
          doctype: p.doctype,
          doctype_name: p.doctype_name || p.doctype,
          role_name: p.role_name || data.name,
          tenant_name: selectedTenantName, // ✅ Используем выбранное имя
          tenant_id: selectedTenantId, // ✅ Используем выбранную организацию
          full_access: p.full_access,
          author: p.author,
          reader: p.reader,
          editor: p.editor,
          can_delete: p.can_delete,
          access_by_tags: p.access_by_tags,
          ...(p.id ? { id: p.id } : {}),
        })),
      user_ids: selectedUserIds,
    };

    const mutationParams =
      isEdit && role?.id
        ? { data: payload, params: { role_id: role.id } }
        : { data: payload };

    saveMutation.mutate(mutationParams, {
      onSuccess: async (res) => {
        if (res.data) {
          const savedRole = res.data;

          // ✅ Правило №24: Строгий порядок действий
          await queryClient.invalidateQueries({ queryKey: ["roles"] });
          if (isEdit && role?.id) {
            await queryClient.invalidateQueries({
              queryKey: ["role", role.id],
            });
            await queryClient.invalidateQueries({
              queryKey: ["permissions", role.id],
            });
          }

          await queryClient.invalidateQueries({
            predicate: (query) => {
              const key = query.queryKey[0];
              return (
                typeof key === "string" && key.toLowerCase().includes("user")
              );
            },
          });

          handleOpenChange(false);
          await onRoleSaved(savedRole.id, savedRole.name);
          toast({ title: "Роль сохранена" });
        }
      },
      onError: (error: unknown) => {
        // ✅ Правило №36: Безопасная обработка ошибок
        const err = error as { response?: { data?: { detail?: string } } };
        toast({
          variant: "destructive",
          title: "Ошибка сохранения",
          description:
            err?.response?.data?.detail || "Не удалось сохранить роль",
        });
      },
    });
  };

  // ✅ Правило №36: Строгая типизация onInvalid
  const onInvalid = (formErrors: FieldErrors<RoleFormData>) => {
    console.warn("Ошибки валидации формы:", formErrors);
    toast({
      variant: "destructive",
      title: "Ошибка заполнения формы",
      description:
        "Пожалуйста, проверьте правильность заполнения полей. Название роли обязательно.",
    });
  };

  // ✅ Правило №37: useEffect ТОЛЬКО для reset формы
  useEffect(() => {
    if (open) {
      if (role) {
        reset({
          name: role.name || "",
          description: role.description || "",
        });
      } else {
        reset(CREATE_DEFAULTS);
      }
    }
  }, [open, role, reset]);

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent
        key={
          open
            ? isEdit
              ? `edit-${role?.id}-${sessionKey}`
              : `create-${sessionKey}`
            : "closed"
        }
        className="max-h-[90vh] items-start pt-8"
        style={{
          width: "800px",
          maxWidth: "800px",
          minHeight: "600px",
          height: "auto",
        }}
      >
        <DialogHeader>
          <DialogTitle>
            {isEdit
              ? `Редактирование роли: ${role.name}`
              : "Создание новой роли"}
          </DialogTitle>
        </DialogHeader>

        {/* ✅ Правило №37: key на форме гарантирует перемонт при смене role */}
        <form
          key={role?.id || "new"}
          onSubmit={handleSubmit(onSubmit, onInvalid)}
          className="space-y-4"
        >
          <Tabs defaultValue="main" className="w-full">
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="main" className="relative">
                Основное
                {hasTenantChanges && (
                  <span className="absolute -top-1 -right-1 text-amber-500 text-xl font-bold leading-none">
                    *
                  </span>
                )}
              </TabsTrigger>

              <TabsTrigger value="sections" className="relative">
                Разделы
                {hasSectionChanges && (
                  <span className="absolute -top-1 -right-1 text-amber-500 text-xl font-bold leading-none">
                    *
                  </span>
                )}
              </TabsTrigger>

              <TabsTrigger value="permissions" className="relative">
                Полномочия
                {hasPermissionChanges && (
                  <span className="absolute -top-1 -right-1 text-amber-500 text-xl font-bold leading-none">
                    *
                  </span>
                )}
              </TabsTrigger>

              <TabsTrigger value="users" className="relative">
                Пользователи
                {hasUserChanges && (
                  <span className="absolute -top-1 -right-1 text-amber-500 text-xl font-bold leading-none">
                    *
                  </span>
                )}
              </TabsTrigger>
            </TabsList>

            {/* Вкладка 1: Основное + Предприятие */}
            <TabsContent value="main" className="space-y-4 mt-0 min-h-[400px]">
              {/* --- СЦЕНАРИЙ A: Создание роли --- */}
              {!isEdit && (
                <div className="space-y-2">
                  <label className="text-sm font-medium flex items-center gap-2">
                    <Building2 className="h-4 w-4 text-muted-foreground" />
                    Предприятие
                  </label>
                  <div className="px-3 py-2 rounded-md border bg-muted/50 text-sm">
                    {selectedTenantName || currentTenantId || "—"}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Роль будет создана для вашего предприятия. Изменить при
                    создании нельзя.
                  </p>
                </div>
              )}

              {/* --- СЦЕНАРИЙ B: Редактирование, обычный Админ (read-only) --- */}
              {isEdit && !isSuperadmin && (
                <div className="space-y-2">
                  <label className="text-sm font-medium flex items-center gap-2">
                    <Building2 className="h-4 w-4 text-muted-foreground" />
                    Предприятие
                  </label>
                  <div className="px-3 py-2 rounded-md border bg-muted/50 text-sm">
                    {role?.tenant_name || role?.tenant_id || "—"}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Изменить предприятие может только суперадмин.
                  </p>
                </div>
              )}

              {/* --- СЦЕНАРИЙ C: Редактирование, Суперадмин (редактируемо) --- */}
              {isEdit && isSuperadmin && (
                <div className="space-y-2">
                  <label className="text-sm font-medium flex items-center gap-2">
                    <Building2 className="h-4 w-4 text-muted-foreground" />
                    Предприятие
                  </label>
                  <ReferenceSelect
                    fetchFn={async (params) => {
                      const response = await readTenantsTenantsGet({
                        skip: params.skip,
                        limit: params.limit,
                        search: params.search,
                      });
                      const items = (response?.items ?? []).map(
                        (t: unknown) => {
                          const tt = t as { id: string; name: string };
                          return { id: tt.id, name: tt.name };
                        },
                      );
                      return { items, total: response?.total ?? 0 };
                    }}
                    queryKey={["tenants-for-role"]}
                    value={selectedTenantId}
                    onValueChange={handleTenantChange} // ✅ Исправлено: соответствует (value: string) => void
                    placeholder="Выберите предприятие..."
                    selectedLabel={
                      selectedTenantName ||
                      role?.tenant_name ||
                      "Выберите предприятие..."
                    }
                    heading="Предприятия"
                  />
                  {hasTenantChanges && (
                    <p className="text-xs text-amber-600">
                      ⚠ Предприятие изменено. Сохраните роль для применения
                      изменений.
                    </p>
                  )}
                </div>
              )}

              <div className="space-y-2">
                <label className="text-sm font-medium">Название роли</label>
                <Controller
                  name="name"
                  control={control}
                  render={({ field, fieldState }) => (
                    <>
                      <Input {...field} placeholder="Например: Бухгалтер" />
                      {fieldState.error && (
                        <p className="text-xs text-destructive">
                          {fieldState.error.message}
                        </p>
                      )}
                    </>
                  )}
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">Описание</label>
                <Controller
                  name="description"
                  control={control}
                  render={({ field }) => (
                    <Textarea
                      {...field}
                      placeholder="Описание роли..."
                      rows={3}
                    />
                  )}
                />
              </div>
            </TabsContent>

            {/* Вкладка 2: Разделы */}
            <TabsContent
              value="sections"
              className="space-y-4 mt-0 min-h-[400px]"
            >
              <div className="space-y-2">
                <label className="text-sm font-medium">Разделы доступа</label>
                <MultiSelectChips
                  fetchFn={async (params) => {
                    const response = await getSectionsSectionsGet({
                      skip: params.skip,
                      limit: params.limit,
                      search: params.search,
                    });
                    const items = (response?.data?.items ?? []).map(
                      (item: unknown) => {
                        const typedItem = item as {
                          id: string;
                          name: string;
                          description?: string | null;
                        };
                        return {
                          id: typedItem.id,
                          name: typedItem.name,
                          description: typedItem.description,
                        };
                      },
                    );
                    return { items, total: response?.data?.total ?? 0 };
                  }}
                  queryKey={["sections"]}
                  value={selectedSectionIds}
                  onValueChange={setSelectedSectionIds}
                  allItems={sections.map((s) => ({ id: s.id, name: s.name }))}
                  placeholder="Добавить разделы..."
                  limit={100}
                  heading="Доступные разделы"
                  columns={[{ column: "description", label: "Описание" }]}
                />
                <p className="text-xs text-muted-foreground">
                  Выбрано разделов: {selectedSectionIds.length}
                </p>
              </div>
            </TabsContent>

            {/* Вкладка 3: Полномочия */}
            <TabsContent
              value="permissions"
              className="space-y-4 mt-0 min-h-[400px]"
            >
              <PermissionsTab
                permissions={permissions}
                onPermissionsChange={setPermissions}
                tenantId={selectedTenantId} // ✅ Используем выбранную организацию
                roleName={role?.name || ""}
              />
            </TabsContent>

            {/* Вкладка 4: Пользователи */}
            <TabsContent value="users" className="space-y-4 mt-0 min-h-[400px]">
              {isUsersLoading ? (
                <div className="flex items-center justify-center h-40">
                  <Loader2 className="h-6 w-6 animate-spin" />
                </div>
              ) : (
                <UsersTab
                  users={usersDraft}
                  onUsersChange={setUsersDraft}
                  allUsers={
                    allUsers as unknown as import("@/api/generated/fastAPI.schemas").UserResponseSchema[]
                  }
                  initialUserIds={initialUserIds}
                />
              )}
            </TabsContent>
          </Tabs>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => handleOpenChange(false)}
            >
              Отмена
            </Button>
            <Button type="submit" disabled={saveMutation.isPending}>
              {saveMutation.isPending && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              <Check className="mr-2 h-4 w-4" />
              Сохранить
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
