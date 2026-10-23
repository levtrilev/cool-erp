import { useState, useMemo, useEffect, useRef, useCallback } from "react";
import {
  useForm,
  Controller,
  type FieldErrors,
  useWatch,
} from "react-hook-form";

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
import {
  readTenantsTenantsGet,
  useReadTenantsTenantsGet,
} from "@/api/generated/tenants/tenants";
import type { RoleResponseSchema } from "@/api/generated/fastAPI.schemas";
import { PermissionsTab, type PermissionDraft } from "./PermissionsTab";
import { UsersTab, type UserDraft } from "./UsersTab";
import {
  ReferenceSelect,
  type ReferenceItem,
} from "@/lib/reusable/ReferenceSelect";
import { ReferenceMultiSelectChips } from "@/lib/reusable/ReferenceMultiSelectChips";

// ✅ Правило №20: Константа для сброса формы
const CREATE_DEFAULTS: RoleFormData = {
  name: "",
  description: "",
  section_ids: [],
};

const roleSchema = z.object({
  name: z.string().min(1, "Название обязательно"),
  description: z.string().optional(),
  section_ids: z.array(z.string()).optional(),
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

  // ✅ НОВОЕ: Сохранённая версия роли — источник истины после успешного сохранения.
  // Проп role из родителя не обновляется автоматически, поэтому используем ответ мутации.
  const [savedRoleOverride, setSavedRoleOverride] =
    useState<RoleResponseSchema | null>(null);
  const effectiveRole: RoleResponseSchema | null =
    savedRoleOverride ?? role ?? null;

  // ✅ НОВОЕ: Триггер принудительной пересинхронизации черновика пользователей
  const [usersResyncKey, setUsersResyncKey] = useState(0);

  // ✅ СТАЛО: синхронизация состояния в обработчике событий, а не в эффекте
  const handleOpenChange = (newOpen: boolean) => {
    if (newOpen && !open) {
      // Открытие модалки — сбрасываем состояние для чистой инициализации
      setSessionKey((prev) => prev + 1);
      setSavedRoleOverride(null); // ✅ Сброс override при открытии новой роли
      setUsersDraft([]); // ✅ Сброс черновика пользователей
      lastInitializedRoleId.current = null; // ✅ Сброс флага инициализации
    }
    if (!newOpen) {
      // Закрытие модалки — сброс формы (Правило №20)
      reset(CREATE_DEFAULTS);
      setSavedRoleOverride(null);
      setUsersDraft([]);
      lastInitializedRoleId.current = null;
    }
    onOpenChange(newOpen);
  };

  // ==========================================
  // ✅ ПОЛЕ ОРГАНИЗАЦИЯ - СОСТОЯНИЕ : единый источник названий
  // ==========================================
  const { data: tenantsData } = useReadTenantsTenantsGet({
    limit: 1000,
    skip: 0,
  });

  const tenants = useMemo<ReferenceItem[]>(() => {
    const response = tenantsData as unknown as {
      items?: ReferenceItem[];
      data?: { items?: ReferenceItem[] };
    };
    return response?.items ?? response?.data?.items ?? [];
  }, [tenantsData]);

  // Пустая строка = "использовать организацию текущего пользователя".
  const [selectedTenantId, setSelectedTenantId] = useState<string>(
    role?.tenant_id ?? "",
  );
  // ✅ Ключ для принудительного перемонта ReferenceSelect при отклонении смены
  const [tenantSelectKey, setTenantSelectKey] = useState(0);

  // ✅ Эффективный ID сам адаптируется к асинхронной загрузке профиля/роли.
  // Никаких setState внутри useEffect (Правило №37).
  const effectiveTenantId = selectedTenantId || currentTenantId || "";

  // ✅ Название — производное значение, а не состояние.
  const selectedTenantName = useMemo<string>(() => {
    // Текущую Организацию берём из профиля: работает даже без справочника.
    if (effectiveTenantId && effectiveTenantId === currentTenantId) {
      const fromProfile = userData?.data?.tenant_name;
      if (fromProfile) return fromProfile;
    }
    return (
      tenants.find((t) => t.id === effectiveTenantId)?.name ??
      effectiveRole?.tenant_name ??
      ""
    );
  }, [
    tenants,
    effectiveTenantId,
    currentTenantId,
    userData?.data?.tenant_name,
    effectiveRole?.tenant_name,
  ]);

  //   ======= END ОРГАНИЗАЦИЯ ===========================

  // Разрешена смена организации (только суперадмин и при создании, и при редактировании)
  const canChangeTenant = isSuperadmin;

  // ✅ Проверка наличия связей перед сменой организации
  // ✅ Исправлено: принимает только (value: string), как требует ReferenceSelect

  const handleTenantChange = (newTenantId: string): void => {
    if (!canChangeTenant || newTenantId === effectiveTenantId) return;

    // Проверяем только СОХРАНЁННЫЕ связи (Правило из ТЗ).
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
        description:
          `Для роли "${effectiveRole?.name}" уже назначены: ${assigned.join(", ")}. ` +
          "Сначала удалите все назначения.",
      });

      // ✅ Принудительный перемонт ReferenceSelect для сброса
      // его внутреннего состояния на текущее значение selectedTenantId
      setTenantSelectKey((prev) => prev + 1);

      return;
    }

    setSelectedTenantId(newTenantId);
    toast({
      title: "Организация изменена",
      description: "Роль будет сохранена для выбранной организации.",
    });
  };

  const hasTenantChanges = useMemo<boolean>(
    () =>
      canChangeTenant &&
      effectiveTenantId !== (effectiveRole?.tenant_id || currentTenantId || ""),
    [
      canChangeTenant,
      effectiveTenantId,
      effectiveRole?.tenant_id,
      currentTenantId,
    ],
  );

  // ==========================================
  // ДАННЫЕ ПОЛЬЗОВАТЕЛЕЙ (НЕ ТРОНУТО)
  // ==========================================
  const { data: usersData, isLoading: isUsersLoading } = useReadUsersUsersGet({
    tenant_id: effectiveTenantId, // ✅ Используем выбранную организацию
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
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const initialUserIds: string[] =
    !roleId || allUsers.length === 0
      ? []
      : allUsers.filter((u) => u.role_ids?.includes(roleId)).map((u) => u.id);

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
  // ✅ СТАЛО: useEffect только для инициализации при загрузке данных
  // Сброс состояния выполняется в handleOpenChange (обработчик событий)
  useEffect(() => {
    if (open && roleId && !isUsersLoading && usersData) {
      if (lastInitializedRoleId.current !== roleId) {
        setUsersDraft(initialUsersDraft);
        lastInitializedRoleId.current = roleId;
      }
    }
  }, [
    open,
    roleId,
    initialUsersDraft,
    isUsersLoading,
    usersData,
    usersResyncKey,
  ]);

  // ✅ selectedUserIds вычисляется из usersDraft (фильтрует помеченных на удаление)
  const selectedUserIds = useMemo(() => {
    return usersDraft.filter((u) => !u.markedForDeletion).map((u) => u.id);
  }, [usersDraft]);

  // ==========================================
  // ДАННЫЕ РАЗДЕЛОВ
  // ==========================================

  const { data: sectionsData } = useGetSectionsSectionsGet({
    target_tenant_id: effectiveTenantId,
    limit: 1000,
    skip: 0,
  });

  const sections = useMemo(
    () => sectionsData?.data?.items ?? [],
    [sectionsData],
  );

  // ==========================================
  // ДАННЫЕ ПОЛНОМОЧИЙ
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
  const [initialPermissionsSnapshot, setInitialPermissionsSnapshot] =
    useState<string>(JSON.stringify(initialPerms));

  // ==========================================
  // ИНДИКАТОРЫ ИЗМЕНЕНИЙ (НЕ ТРОНУТО)
  // ==========================================
  const hasPermissionChanges = useMemo(() => {
    return JSON.stringify(permissions) !== initialPermissionsSnapshot;
  }, [permissions, initialPermissionsSnapshot]);

  // ✅ НОВОЕ: Количество активных (не помеченных на удаление) полномочий для счётчика на вкладке
  const activePermissionsCount = useMemo(
    () => permissions.filter((p) => !p.markedForDeletion).length,
    [permissions],
  );

  // ✅ Мемоизированное вычисление sectionIds.

  const sectionIds = useWatch({
    control,
    name: "section_ids",
    defaultValue: [],
  });

  const initialSectionIds = useMemo<string[]>(
    () => effectiveRole?.section_ids || [],
    [effectiveRole],
  );

  const newSectionIds = useMemo<string[]>(
    () => (sectionIds || []).filter((id) => !initialSectionIds.includes(id)),
    [sectionIds, initialSectionIds],
  );

  const deletedSectionIds = useMemo<string[]>(
    () => initialSectionIds.filter((id) => !(sectionIds || []).includes(id)),
    [sectionIds, initialSectionIds],
  );

  // // ✅ ID разделов, добавленных в текущей сессии (для пометки "новый")
  // const newSectionIds = useMemo<string[]>(() => {
  //   const initial = effectiveRole?.section_ids || [];
  //   return (sectionIds || []).filter((id) => !initial.includes(id));
  // }, [sectionIds, effectiveRole?.section_ids]);

  const hasSectionChanges = useMemo(() => {
    const initial = (effectiveRole?.section_ids || []).slice().sort();
    const current = (sectionIds || []).slice().sort();
    return JSON.stringify(initial) !== JSON.stringify(current);
  }, [effectiveRole?.section_ids, sectionIds]);

  const hasUserChanges = useMemo(() => {
    const initial = initialUserIds.slice().sort();
    const current = selectedUserIds.slice().sort();
    return JSON.stringify(initial) !== JSON.stringify(current);
  }, [initialUserIds, selectedUserIds]);

  const hasAnyChanges: boolean =
    hasTenantChanges ||
    hasSectionChanges ||
    hasPermissionChanges ||
    hasUserChanges;

  // ==========================================
  // ОБРАБОТЧИКИ
  // ==========================================
  const saveMutation = useSaveRoleRolesSavePost();

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const onSubmit = async (data: RoleFormData) => {
    if (!effectiveTenantId) {
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
      tenant_id: effectiveTenantId,
      section_ids: sectionIds,
      section_names: sections
        .filter((s) => (sectionIds || []).includes(s.id))
        .map((s) => s.name),
      permissions: permissions
        .filter((p) => !p.markedForDeletion)
        .map((p) => ({
          doctype: p.doctype,
          doctype_name: p.doctype_name || p.doctype,
          role_name: p.role_name || data.name,
          tenant_name: selectedTenantName,
          tenant_id: effectiveTenantId,
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

          // ✅ Правило №24: Инвалидация кэшей
          await queryClient.invalidateQueries({ queryKey: ["roles"] });
          if (isEdit && role?.id) {
            await queryClient.invalidateQueries({
              queryKey: ["role", role.id],
            });
            await queryClient.invalidateQueries({
              queryKey: ["permissions", role.id],
            });
          }

          // ✅ Дожидаемся актуальных данных пользователей,
          // чтобы пересинхронизация черновика произошла на свежих данных
          await queryClient.refetchQueries({
            predicate: (query) => {
              const key = query.queryKey[0];
              return (
                typeof key === "string" && key.toLowerCase().includes("user")
              );
            },
          });

          // ✅ 1. Обновляем источник истины на сохранённую версию
          setSavedRoleOverride(savedRole);

          // ✅ 2. Синхронизируем черновик полномочий с ответом бэкенда.
          // Все записи имеют id → пометка "(новый)" исчезнет.
          // Нет поля markedForDeletion → пометка "(будет удалено)" исчезнет.
          const freshPerms: PermissionDraft[] = (
            savedRole.permissions ?? []
          ).map((p) => ({
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
          }));
          setPermissions(freshPerms);
          // ✅ Синхронизируем снапшот → индикатор "*" на вкладке Полномочия исчезнет
          setInitialPermissionsSnapshot(JSON.stringify(freshPerms));

          // ✅ 3. Пересинхронизируем черновик пользователей.
          // Сбрасываем флаг инициализации и триггерим useEffect через usersResyncKey.
          // После обновления usersData все пользователи будут в initialUserIds →
          // пометки "(новый)" и "(будет удалён)" исчезнут, индикатор "*" сбросится.
          lastInitializedRoleId.current = null;
          setUsersResyncKey((prev) => prev + 1);

          // ✅ 4. Модалку НЕ закрываем. Обновляем список родителя.
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

  // ✅ Правило №36: Строгая типизация onInvalid
  // eslint-disable-next-line react-hooks/exhaustive-deps
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
  // ✅ СТАЛО: useEffect только для reset формы (без setState)
  useEffect(() => {
    if (open && effectiveRole) {
      reset({
        name: effectiveRole.name || "",
        description: effectiveRole.description || "",
        section_ids: effectiveRole.section_ids || [],
      });
    } else if (open && !effectiveRole) {
      reset(CREATE_DEFAULTS);
    }
  }, [open, effectiveRole, reset]);

  // ✅ Мемоизированный обработчик формы для предотвращения
  // чтения useRef во время рендера (ошибка React Compiler)
  // const handleFormSubmit: React.FormEventHandler<HTMLFormElement> = useCallback(
  //   (e) => {
  //     handleSubmit(onSubmit, onInvalid)(e);
  //   },
  //   [handleSubmit, onSubmit, onInvalid],
  // );
  const handleFormSubmit: React.FormEventHandler<HTMLFormElement> = useCallback(
    (e) => {
      handleSubmit(onSubmit, onInvalid)(e);
    },
    [handleSubmit, onSubmit, onInvalid],
  );

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
              ? `Редактирование роли: ${effectiveRole?.name}`
              : "Создание новой роли"}
          </DialogTitle>
        </DialogHeader>

        {/* ✅ Правило №37: key на форме гарантирует перемонт при смене role */}
        <form
          key={role?.id || "new"}
          onSubmit={handleFormSubmit}
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

              {/* ✅ Счётчик разделов */}
              <TabsTrigger value="sections" className="relative">
                Разделы({(sectionIds || []).length})
                {hasSectionChanges && (
                  <span className="absolute -top-1 -right-1 text-amber-500 text-xl font-bold leading-none">
                    *
                  </span>
                )}
              </TabsTrigger>

              {/* ✅ Счётчик полномочий (типов документов) */}
              <TabsTrigger value="permissions" className="relative">
                Полномочия({activePermissionsCount})
                {hasPermissionChanges && (
                  <span className="absolute -top-1 -right-1 text-amber-500 text-xl font-bold leading-none">
                    *
                  </span>
                )}
              </TabsTrigger>

              {/* ✅ Счётчик пользователей */}
              <TabsTrigger value="users" className="relative">
                Пользователи({selectedUserIds.length})
                {hasUserChanges && (
                  <span className="absolute -top-1 -right-1 text-amber-500 text-xl font-bold leading-none">
                    *
                  </span>
                )}
              </TabsTrigger>
            </TabsList>

            {/* Вкладка 1: Основное + Организация */}
            <TabsContent value="main" className="space-y-4 mt-0 min-h-[400px]">
              {/* --- Обычный Админ: всегда только чтение --- */}
              {!isSuperadmin && (
                <div className="space-y-2">
                  <label className="text-sm font-medium flex items-center gap-2">
                    <Building2 className="h-4 w-4 text-muted-foreground" />
                    Организация
                  </label>
                  <div className="px-3 py-2 rounded-md border bg-muted/50 text-sm">
                    {selectedTenantName || effectiveTenantId || "—"}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {isEdit
                      ? "Изменить организацию может только суперадмин."
                      : "Роль будет создана для вашей организации."}
                  </p>
                </div>
              )}

              {/* --- Суперадмин: выбор и при создании, и при редактировании --- */}
              {isSuperadmin && (
                <div className="space-y-2">
                  <label className="text-sm font-medium flex items-center gap-2">
                    <Building2 className="h-4 w-4 text-muted-foreground" />
                    Организация
                  </label>
                  <ReferenceSelect
                    key={tenantSelectKey} // ✅ Перемонт при отклонении смены
                    fetchFn={async (params) => {
                      const response = await readTenantsTenantsGet({
                        skip: params.skip,
                        limit: params.limit,
                        search: params.search,
                      });

                      // ✅ Адаптер: приводим к ReferenceItem с индексной сигнатурой
                      const items: ReferenceItem[] = (
                        response?.items ?? []
                      ).map((t) => ({
                        id: t.id,
                        name: t.name,
                      }));

                      return {
                        items,
                        total: response?.total ?? 0,
                      };
                    }}
                    queryKey={["tenants-for-role"]}
                    value={selectedTenantId}
                    onValueChange={handleTenantChange}
                    placeholder="Выберите организацию..."
                    selectedLabel={
                      selectedTenantName || "Выберите организацию..."
                    }
                    heading="Организации"
                  />
                  {hasTenantChanges && (
                    <p className="text-xs text-amber-600">
                      ⚠ Организация изменена. Сохраните роль для применения
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
                <Controller
                  name="section_ids"
                  control={control}
                  render={({ field }) => (
                    <ReferenceMultiSelectChips
                      fetchFn={async (params) => {
                        const response = await getSectionsSectionsGet({
                          skip: params.skip,
                          limit: params.limit,
                          search: params.search,
                          target_tenant_id: effectiveTenantId,
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
                      queryKey={["sections", effectiveTenantId]}
                      value={field.value ?? []}
                      onValueChange={field.onChange}
                      allItems={sections.map((s) => ({
                        id: s.id,
                        name: s.name,
                      }))}
                      newItemIds={newSectionIds}
                      deletedItemIds={deletedSectionIds}
                      placeholder="Добавить разделы..."
                      limit={100}
                      heading="Доступные разделы"
                      columns={[{ column: "description", label: "Описание" }]}
                    />
                  )}
                />
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
                tenantId={effectiveTenantId}
                roleName={effectiveRole?.name || ""}
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
              className="min-w-24"
              onClick={() => handleOpenChange(false)}
            >
              {hasAnyChanges ? "Отмена" : "Закрыть"}
            </Button>
            {/* <Button type="submit" disabled={saveMutation.isPending}> */}
            <Button type="submit" disabled={!hasAnyChanges}>
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
