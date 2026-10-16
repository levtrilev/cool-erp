import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/components/ui/use-toast";
import { useGetUserAuthUserGet, useUpdateUserAuthUserIdPut } from "@/api/generated/authentication/authentication";
import { readUsersAuthGetResponse } from "@/api/generated/zod/authentication/authentication.schema";
import { ReferenceSelect } from "@/lib/reusable/ReferenceSelect";
import { readTenantsTenantsGet } from "@/api/generated/tenants/tenants";
import { useEffect, useState } from "react";
import { Plus, Tag, X } from "lucide-react";
import { Badge } from "@/components/ui/badge";

// ✅ Валидация формата тега (ТЗ §6.2.1–6.2.3)
// Формат: <пространство>:<значение>, без пробелов, регистр значим
const TAG_REGEX = /^[^\s:]+:[^\s:]+$/;

const editUserSchema = z.object({
  name: z.string().min(2, "Имя должно содержать минимум 2 символа"),
  email: z.string().email("Некорректный email"),
  password: z
    .string()
    .min(8, "Пароль должен содержать минимум 8 символов")
    .optional()
    .or(z.literal("")),
  tenant_id: z.string().uuid("Выберите организацию"),
  tags: z.array(z.string()).optional(),
});

type EditUserFormData = z.infer<typeof editUserSchema>;

// ✅ Извлекаем тип из Zod-схемы (гарантированно работает)
type UserResponseSchema = z.infer<
  typeof readUsersAuthGetResponse
>["items"][number];

interface EditUserModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  user: UserResponseSchema | null;
  onUserUpdated: (userId: string, userName: string) => Promise<void>;
}

export const EditUserModal = ({
  open,
  onOpenChange,
  user,
  onUserUpdated,
}: EditUserModalProps) => {
  const { toast } = useToast();
  const updateUserMutation = useUpdateUserAuthUserIdPut();

    // ✅ Определяем права текущего пользователя (ТЗ §6.3.2: теги назначает только Админ/Суперадмин)
  const { data: currentUserData } = useGetUserAuthUserGet();
  const canEditTags =
    currentUserData?.data?.is_admin === true ||
    currentUserData?.data?.is_superadmin === true;
    
  const {
    register,
    handleSubmit,
    control, // ✅ Добавляем control для Controller
    formState: { errors, isDirty },
    reset,
  } = useForm<EditUserFormData>({
    resolver: zodResolver(editUserSchema),
    defaultValues: {
      name: "",
      email: "",
      password: "",
      tenant_id: "",
    },
  });

  // ✅ Состояние для ввода нового тега
  const [tagInput, setTagInput] = useState("");
  const [tagError, setTagError] = useState<string | null>(null);

  useEffect(() => {
    if (open && user) {
      reset({
        name: user.name,
        email: user.email,
        password: "",
        tenant_id: user.tenant_id || "", // ✅ Controller автоматически подхватит это значение
        tags: (user as unknown as { tags?: string[] })?.tags ?? [],
      });
    }
  }, [open, user, reset]);
  
    // ✅ Добавление тега с валидацией формата (ТЗ §6.2)
  const handleAddTag = (
    currentTags: string[],
    onChange: (tags: string[]) => void,
  ) => {
    const trimmed = tagInput.trim();
    if (!trimmed) return;

    // Проверка формата (ТЗ §6.2.1–6.2.2)
    if (!TAG_REGEX.test(trimmed)) {
      setTagError(
        "Формат тега: пространство:значение (без пробелов). Пример: регион:сибирь",
      );
      return;
    }

    // Проверка на дубликат (ТЗ §6.2.3: регистр значим)
    if (currentTags.includes(trimmed)) {
      setTagError(`Тег "${trimmed}" уже добавлен`);
      return;
    }

    onChange([...currentTags, trimmed]);
    setTagInput("");
    setTagError(null);
  };

    // ✅ Удаление тега
  const handleRemoveTag = (
    tagToRemove: string,
    currentTags: string[],
    onChange: (tags: string[]) => void,
  ) => {
    onChange(currentTags.filter((t) => t !== tagToRemove));
  };

  const onSubmit = (data: EditUserFormData) => {
    if (!user?.id) return;

    const updateData = {
      name: data.name,
      email: data.email,
      ...(data.password ? { password: data.password } : {}),
      tenant_id: data.tenant_id,
      tags: data.tags ?? [],
    };

    updateUserMutation.mutate(
      {
        userId: user.id,
        data: updateData,
      },
      {
        onSuccess: async () => {
          toast({
            title: "Пользователь обновлен",
            description: `Данные ${data.name} успешно изменены`,
          });

          // ✅ Передаём ID и новое имя в родительский компонент
          await onUserUpdated(user.id, data.name);

          onOpenChange(false);
        },
        onError: (error: unknown) => {
          let message = "Ошибка обновления пользователя";

          if (error && typeof error === "object" && "response" in error) {
            const response = (
              error as { response?: { data?: { detail?: string } } }
            ).response;
            if (response?.data?.detail) {
              message = response.data.detail;
            }
          }

          toast({
            variant: "destructive",
            title: "Ошибка",
            description: message,
          });
        },
      },
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Редактирование пользователя</DialogTitle>
          <DialogDescription>
            Измените данные пользователя {user?.name}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="edit-name">Имя</Label>
            <Input id="edit-name" {...register("name")} />
            {errors.name && (
              <p className="text-sm text-destructive">{errors.name.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="edit-email">Email</Label>
            <Input id="edit-email" type="email" {...register("email")} />
            {errors.email && (
              <p className="text-sm text-destructive">{errors.email.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="edit-password">
              Новый пароль{" "}
              <span className="text-muted-foreground text-xs">
                (оставьте пустым, если не хотите менять)
              </span>
            </Label>
            <Input
              id="edit-password"
              type="password"
              {...register("password")}
            />
            {errors.password && (
              <p className="text-sm text-destructive">
                {errors.password.message}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label>Организация</Label>

            {/* ✅ Controller связывает Generic-компонент с формой, не нарушая его универсальность */}
            <Controller
              name="tenant_id"
              control={control}
              render={({ field }) => (
                <ReferenceSelect
                  fetchFn={async (params) => {
                    const response = await readTenantsTenantsGet(params);
                    // Распаковываем ApiResponse -> { items, total }
                    return {
                      items: response?.items ?? [],
                      total: response?.total ?? 0,
                    };
                  }}
                  queryKey={["tenants", "active"]} // ✅ Чистый ключ кэша, без специфики пользователя
                  value={field.value || ""} // ✅ Значение берется напрямую из формы
                  onValueChange={field.onChange} // ✅ Изменение сразу идет в форму
                  placeholder="Выберите организацию"
                  selectedLabel={user?.tenant_name ?? "Выберите организацию"}
                  heading="Выберите организацию"
                  columns={[
                    { column: "description", label: "Описание" },
                    // { column: "name", label: "Название полное" },
                  ]}
                />
              )}
            />

            {errors.tenant_id && (
              <p className="text-sm text-destructive">
                {errors.tenant_id.message}
              </p>
            )}
          </div>

         {/* ✅ НОВОЕ: Редактор тегов доступа (ТЗ §6.3) */}
          <div className="space-y-2">
            <Label className="flex items-center gap-2">
              <Tag className="h-4 w-4 text-muted-foreground" />
              Теги доступа
              <span className="text-xs text-muted-foreground font-normal">
                (формат: пространство:значение)
              </span>
            </Label>

            <Controller
              name="tags"
              control={control}
              render={({ field }) => {
                const tags = field.value ?? [];
                return (
                  <div className="space-y-2">
                    {/* Отображение текущих тегов */}
                    {tags.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 p-2 rounded-md border bg-muted/30 min-h-[36px]">
                        {tags.map((tag) => (
                          <Badge
                            key={tag}
                            variant="secondary"
                            className="text-xs gap-1 pr-1"
                          >
                            {tag}
                            {canEditTags && (
                              <button
                                type="button"
                                onClick={() =>
                                  handleRemoveTag(tag, tags, field.onChange)
                                }
                                className="ml-0.5 rounded-full hover:bg-muted-foreground/20 p-0.5"
                                title={`Удалить тег ${tag}`}
                              >
                                <X className="h-3 w-3" />
                              </button>
                            )}
                          </Badge>
                        ))}
                      </div>
                    )}

                    {tags.length === 0 && (
                      <p className="text-xs text-muted-foreground px-2 py-1">
                        Теги не назначены
                      </p>
                    )}

                    {/* Ввод нового тега (только для Админа/Суперадмина — ТЗ §6.3.2) */}
                    {canEditTags && (
                      <div className="flex gap-2">
                        <Input
                          value={tagInput}
                          onChange={(e) => {
                            setTagInput(e.target.value);
                            setTagError(null);
                          }}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") {
                              e.preventDefault();
                              handleAddTag(tags, field.onChange);
                            }
                          }}
                          placeholder="регион:сибирь"
                          className="flex-1"
                        />
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => handleAddTag(tags, field.onChange)}
                          disabled={!tagInput.trim()}
                          className="shrink-0"
                        >
                          <Plus className="h-4 w-4 mr-1" />
                          Добавить
                        </Button>
                      </div>
                    )}

                    {/* Ошибка валидации тега */}
                    {tagError && (
                      <p className="text-xs text-destructive">{tagError}</p>
                    )}

                    {/* Подсказка */}
                    <p className="text-xs text-muted-foreground">
                      Теги определяют доступ пользователя к документам с
                      соответствующими тегами. Примеры: регион:сибирь,
                      отдел:бухгалтерия, гриф:секретно
                    </p>
                  </div>
                );
              }}
            />
          </div>

          <DialogFooter className="gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Отмена
            </Button>
            <Button
              type="submit"
              disabled={updateUserMutation.isPending || !isDirty}
            >
              {updateUserMutation.isPending ? "Сохранение..." : "Сохранить"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};
