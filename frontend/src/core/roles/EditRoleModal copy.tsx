import { useState, useMemo, useEffect, useRef } from "react";
import { useForm, Controller, type FieldErrors } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useQueryClient } from "@tanstack/react-query";
import { Loader2, Check } from "lucide-react";
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
import type { RoleResponseSchema } from "@/api/generated/fastAPI.schemas";
import { PermissionsTab, type PermissionDraft } from "./PermissionsTab";
import { UsersTab, type UserDraft } from "./UsersTab";
import { MultiSelectChips } from "@/lib/reusable/MultiSelectChips";

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
  // ДАННЫЕ ПОЛЬЗОВАТЕЛЕЙ (РАБОТАЕТ)
  // ==========================================
  const { data: usersData, isLoading: isUsersLoading } = useReadUsersUsersGet({
    tenant_id: currentTenantId ?? "",
    limit: 1000,
    skip: 0,
  });

  const allUsers = useMemo(() => {
    return (usersData?.items ?? []).map((u) => ({
      id: u.id,
      name: u.name,
      email: u.email,
      role_ids: (u as unknown as UserWithRoles).role_ids || [],
    }));
  }, [usersData]);

  const roleId = role?.id;

  const initialUserIds = useMemo(() => {
    if (!roleId || allUsers.length === 0) return [];
    return allUsers
      .filter((u) => u.role_ids?.includes(roleId))
      .map((u) => u.id);
  }, [roleId, allUsers]);

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

  const [usersDraft, setUsersDraft] = useState<UserDraft[]>([]);
  const lastInitializedRoleId = useRef<string | null>(null);
  const role_id = role?.id;

  useEffect(() => {
    if (open) {
      if (role_id) {
        if (!isUsersLoading && usersData) {
          if (lastInitializedRoleId.current !== role_id) {
            setUsersDraft(initialUsersDraft);
            lastInitializedRoleId.current = role_id;
          }
        }
      } else {
        // eslint-disable-next-line react-hooks/set-state-in-effect
        setUsersDraft([]);
        lastInitializedRoleId.current = null;
      }
    } else {
      setUsersDraft([]);
      lastInitializedRoleId.current = null;
    }
  }, [open, role_id, initialUsersDraft, isUsersLoading, usersData]);

  const selectedUserIds = useMemo(() => {
    return usersDraft.filter((u) => !u.markedForDeletion).map((u) => u.id);
  }, [usersDraft]);

  // ==========================================
  // ДАННЫЕ РАЗДЕЛОВ (ИСПРАВЛЕНО)
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

  // ✅ ИСПРАВЛЕНИЕ: Вычисляем объекты для отображения чипов (как в copy 06)
  //   const selectedSections = useMemo(() => {
  //     return sections
  //       .filter((s) => selectedSectionIds.includes(s.id))
  //       .map((s) => ({ id: s.id, name: s.name, description: s.name }));
  //   }, [sections, selectedSectionIds]);

  // ==========================================
  // ДАННЫЕ ПОЛНОМОЧИЙ (РАБОТАЕТ)
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
  // ИНДИКАТОРЫ ИЗМЕНЕНИЙ
  // ==========================================
  const hasPermissionChanges = useMemo(() => {
    return JSON.stringify(permissions) !== initialPermissionsSnapshot;
  }, [permissions, initialPermissionsSnapshot]);

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
  // ОБРАБОТЧИКИ
  // ==========================================
  const saveMutation = useSaveRoleRolesSavePost();

  const onSubmit = async (data: RoleFormData) => {
    if (!currentTenantId) {
      toast({
        variant: "destructive",
        title: "Ошибка",
        description: "Не удалось определить организацию",
      });
      return;
    }

    const payload = {
      name: data.name,
      description: data.description || "",
      tenant_id: currentTenantId,
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
          tenant_name: "",
          tenant_id: currentTenantId,
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

        <form
          key={role?.id || "new"}
          onSubmit={handleSubmit(onSubmit, onInvalid)}
          className="space-y-4"
        >
          <Tabs defaultValue="main" className="w-full">
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="main">Основное</TabsTrigger>

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

            {/* Вкладка 1: Основное */}
            <TabsContent value="main" className="space-y-4 mt-0 min-h-[400px]">
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

            {/* Вкладка 2: Разделы (ИСПРАВЛЕНО: добавлен проп selectedItems) */}
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
                  //   selectedItems={selectedSections} // ✅ КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ
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
                tenantId={currentTenantId || ""}
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
