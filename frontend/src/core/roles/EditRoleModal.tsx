import { useState, useEffect } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useQueryClient } from "@tanstack/react-query";
import { Loader2, Check } from "lucide-react";
import { useToast } from "@/components/ui/use-toast";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

// Orval хуки и типы
// ⚠️ Убедитесь, что вы перегенерировали Orval после добавления эндпоинта /save и поля permissions в RoleResponseSchema
import { useSaveRoleRolesSavePost } from "@/api/generated/roles/roles";
// import { useReadSectionsSectionsGet } from "@/api/generated/sections/sections";
// import { useUpdateRoleRolesRoleIdPut } from "@/api/generated/roles/roles";
import { useGetSectionsSectionsGet } from "@/api/generated/sections/sections";
import { useReadUsersUsersGet } from "@/api/generated/users/users";
import type {
  RoleResponseSchema,
  // PermissionCreateSchema,
} from "@/api/generated/fastAPI.schemas";
import { useGetUserAuthUserGet } from "@/api/generated/authentication/authentication";
import { PermissionsTab } from "./PermissionsTab";

// ✅ Константа для сброса формы (Правило №20)
const CREATE_DEFAULTS: RoleFormData = {
  name: "",
  description: "",
  // section_ids: [],
  // ⚠️ Добавьте сюда ВСЕ остальные поля, которые есть в вашей Zod-схеме!
  // Например: section_ids: [], user_ids: [] и т.д.
};

// Схема валидации
const roleSchema = z.object({
  name: z.string().min(1, "Название обязательно"),
  description: z.string().optional(),
});
type RoleFormData = z.infer<typeof roleSchema>;

// Заглушка для типов документов (в будущем можно получать с бэкенда через GET /doctypes)
// const AVAILABLE_DOCTYPES = [
//   { doctype: "invoices", doctype_name: "Счета-фактуры" },
//   { doctype: "orders", doctype_name: "Заказы" },
//   { doctype: "contracts", doctype_name: "Договоры" },
//   { doctype: "payments", doctype_name: "Платежи" },
// ];
// const AVAILABLE_DOCTYPES = [] as { doctype: string; doctype_name: string }[];
interface EditRoleModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  role?: RoleResponseSchema | null;
  onRoleSaved: (id: string, name: string) => void;
}

export function EditRoleModal({
  open,
  onOpenChange,
  role,
  onRoleSaved,
}: EditRoleModalProps) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  // ✅ Получаем данные текущего пользователя для tenant_id
  const { data: userData } = useGetUserAuthUserGet();
  const currentTenantId = userData?.data?.tenant_id;

  const isEdit = !!role; // Режим редактирования или создания

  // ✅ Инициализация формы с данными существующей роли
  const { control, handleSubmit, reset } = useForm<RoleFormData>({
    resolver: zodResolver(roleSchema),
    defaultValues: CREATE_DEFAULTS,
  });

  const [selectedSectionIds, setSelectedSectionIds] = useState<string[]>(
    role?.section_ids || [],
  );
  // ✅ Инициализация состояний на основе пропса `role`
  // ✅ Синхронизация формы с данными роли (редактирование vs создание)
useEffect(() => {
  if (role) {
    // Режим редактирования: заполняем форму данными из БД
    reset({
      name: role.name || "",
      description: role.description || "",
      // ⚠️ Добавьте сюда все остальные поля из RoleFormData
    });
  } else {
    // Режим создания: сбрасываем форму к пустым значениям
    reset(CREATE_DEFAULTS);
  }
}, [role, reset]); // Зависимости: role и функция reset


  // В будущем здесь можно парсить role.user_ids, если добавим это поле в RoleResponseSchema
  const [selectedUserIds, setSelectedUserIds] = useState<string[]>([]);

  // Загрузка данных для вкладок (справочники)
  const { data: sectionsData } = useGetSectionsSectionsGet({
    limit: 1000,
    skip: 0,
  });
  const { data: usersData } = useReadUsersUsersGet({ limit: 1000, skip: 0 });

  const sections = sectionsData?.data?.items ?? [];
  const users = usersData?.items ?? [];

  // ✅ Используем агрегирующий эндпоинт сохранения, а не стандартный PUT
  const saveMutation = useSaveRoleRolesSavePost();

  // const onSubmit_bak = async (data: RoleFormData) => {
  //   // ✅ Проверка tenant_id
  //   if (!currentTenantId) {
  //     toast({
  //       variant: "destructive",
  //       title: "Ошибка",
  //       description: "Не удалось определить организацию",
  //     });
  //     return;
  //   }

  //   // ✅ Заполняем tenant_id для каждого разрешения
  //   // const permissionsWithIds = permissions.map((perm) => ({
  //   //   ...perm,
  //   //   role_id: role?.id || "", // ✅ Пустой при создании (бэкенд заполнит)
  //   //   tenant_id: currentTenantId,

  //   // }));

  //   const permissionsWithIds = permissions.map((perm) => {
  //     const item: PermissionCreateSchema = {
  //       ...perm,
  //       tenant_id: currentTenantId,
  //     };

  //     // ✅ Добавляем role_id только если он есть
  //     if (role?.id) {
  //       item.role_id = role.id;
  //     }

  //     return item;
  //   });

  //   const sectionNames = sections
  //     .filter((s) => selectedSectionIds.includes(s.id))
  //     .map((s) => s.name);

  //   const payload = {
  //     name: data.name,
  //     description: data.description,
  //     tenant_id: currentTenantId, // ✅ Всегда из сессии
  //     section_ids: selectedSectionIds,
  //     section_names: sectionNames,
  //     permissions: permissionsWithIds,
  //     user_ids: selectedUserIds,
  //   };

  //   // ✅ Формируем параметры мутации в зависимости от режима
  //   const mutationParams = isEdit
  //     ? { data: payload, params: { role_id: role.id } }
  //     : { data: payload }; // ✅ При создании role_id не передаём

  //   saveMutation.mutate(
  //     // ⚠️ Проверьте имя хука в сгенерированном Orval файле.
  //     // Обычно это { data: payload, roleId: role.id } или { data: payload, queryParams: { role_id: role.id } }
  //     mutationParams,
  //     {
  //       onSuccess: async (res) => {
  //         if (res.data) {
  //           const savedRole = res.data;

  //           // ✅ Правило №24: Строгий порядок
  //           // 1. Инвалидируем кэш
  //           queryClient.invalidateQueries({ queryKey: ["roles"] });
  //           // 2. Закрываем модалку
  //           onOpenChange(false);
  //           // 3. Вызываем callback родителя для умной навигации и подсветки
  //           await onRoleSaved(savedRole.id, savedRole.name);
  //         }
  //       },
  //       onError: () => {
  //         toast({
  //           variant: "destructive",
  //           title: "Ошибка",
  //           description: "Не удалось сохранить роль",
  //         });
  //       },
  //     },
  //   );
  // };
  const onSubmit = async (data: RoleFormData) => {
    // ✅ Проверка tenant_id
    if (!currentTenantId) {
      toast({
        variant: "destructive",
        title: "Ошибка",
        description: "Не удалось определить организацию",
      });
      return;
    }

    // ✅ Payload содержит ТОЛЬКО данные самой роли.
    // Полномочия (permissions) уже сохранены/удалены независимо через компонент PermissionsTab!
    const payload = {
      name: data.name,
      description: data.description || "",
      tenant_id: currentTenantId,

      // ⚠️ Если ваш RoleSaveSchema на бэкенде ТРЕБУЕТ section_ids или user_ids,
      // оставьте их здесь. Но permissions здесь быть НЕ ДОЛЖНО.
      section_ids: selectedSectionIds,
      // user_ids: selectedUserIds,
    };

    // ✅ Формируем параметры мутации в зависимости от режима
    // Примечание: проверьте точную сигнатуру сгенерированного Orval хука saveRoleRolesSavePost
    const mutationParams =
      isEdit && role?.id
        ? { data: payload, params: { role_id: role.id } } // или { roleId: role.id } в зависимости от Orval
        : { data: payload };

    saveMutation.mutate(mutationParams, {
      // 'as any' временно, пока не уточним точную сигнатуру Orval
      onSuccess: async (res) => {
        if (res.data) {
          const savedRole = res.data;

          // ✅ Правило №24: Строгий порядок действий
          // 1. Инвалидируем кэш ДО закрытия модалки
          await queryClient.invalidateQueries({ queryKey: ["roles"] });
          if (isEdit && role?.id) {
            await queryClient.invalidateQueries({
              queryKey: ["role", role.id],
            });
          }

          // 2. Закрываем модалку
          onOpenChange(false);

          // 3. ✅ Правило №20: Сброс формы при закрытии
          reset(CREATE_DEFAULTS);

          // 4. Вызываем callback родителя для умной навигации и подсветки
          await onRoleSaved(savedRole.id, savedRole.name);
        }
      },
      onError: (error: unknown) => {
        // ✅ Безопасное приведение типа для извлечения detail из ответа сервера
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

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      {/* <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto"> */}
      {/* <DialogContent className="w-[2100px] max-h-[90vh] overflow-y-auto"> */}
      <DialogContent
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

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <Tabs defaultValue="main" className="w-full">
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="main">Основное</TabsTrigger>
              <TabsTrigger value="sections">Разделы</TabsTrigger>
              <TabsTrigger value="permissions">Полномочия</TabsTrigger>
              <TabsTrigger value="users">Пользователи</TabsTrigger>
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

            {/* Вкладка 2: Разделы */}
            <TabsContent
              value="sections"
              className="space-y-4 mt-0 min-h-[400px]"
            >
              <div className="rounded-md border max-h-[400px] overflow-y-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="h-10 hover:bg-transparent sticky top-0 bg-background z-10 shadow-sm">
                      <TableHead className="w-[50px]"></TableHead>
                      <TableHead>Название раздела</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {sections.map((section) => (
                      <TableRow key={section.id} className="py-1">
                        <TableCell>
                          <Checkbox
                            checked={selectedSectionIds.includes(section.id)}
                            onCheckedChange={(checked) => {
                              setSelectedSectionIds((prev) =>
                                checked
                                  ? [...prev, section.id]
                                  : prev.filter((id) => id !== section.id),
                              );
                            }}
                          />
                        </TableCell>
                        <TableCell className="py-1 font-medium">
                          {section.name}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </TabsContent>

            {/* Вкладка 3: Полномочия */}
            <TabsContent
              value="permissions"
              className="space-y-4 mt-0 min-h-[400px]"
            >
              {/* 
                Передаем объект роли. 
                ВАЖНО: Если в вашем коде переменная с данными роли называется иначе 
                (например, initialRole, selectedRole или form.getValues()), 
                замените `role` на имя вашей переменной.
              */}
              <PermissionsTab role={role as RoleResponseSchema} />
            </TabsContent>

            {/* Вкладка 4: Пользователи */}
            <TabsContent value="users" className="space-y-4 mt-0 min-h-[400px]">
              <div className="rounded-md border max-h-[400px] overflow-y-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="h-10 hover:bg-transparent sticky top-0 bg-background z-10 shadow-sm">
                      <TableHead className="w-[50px]"></TableHead>
                      <TableHead>Имя</TableHead>
                      <TableHead>Email</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {users.map((user) => (
                      <TableRow key={user.id} className="py-1">
                        <TableCell>
                          <Checkbox
                            checked={selectedUserIds.includes(user.id)}
                            onCheckedChange={(checked) => {
                              setSelectedUserIds((prev) =>
                                checked
                                  ? [...prev, user.id]
                                  : prev.filter((id) => id !== user.id),
                              );
                            }}
                          />
                        </TableCell>
                        <TableCell className="py-1 font-medium">
                          {user.name}
                        </TableCell>
                        <TableCell className="py-1 text-muted-foreground">
                          {user.email}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </TabsContent>
          </Tabs>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
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
