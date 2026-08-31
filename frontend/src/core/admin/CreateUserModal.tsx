import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useState } from "react";
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
import { ReferenceSelect } from "@/core/ReferenceSelect";

// ✅ Импортируем Orval-хуки (проверьте точные имена в сгенерированных файлах)
import { useRegisterAuthRegisterPost } from "@/api/generated/authentication/authentication";
import { getTenantsTenantsGet } from "@/api/generated/tenants/tenants";

// Схема валидации
const createUserSchema = z.object({
  name: z.string().min(2, "Имя должно содержать минимум 2 символа"),
  email: z.string().email("Некорректный email"),
  password: z.string().min(8, "Пароль должен содержать минимум 8 символов"),
  tenant_id: z.string().uuid("Выберите организацию"),
});

type CreateUserFormData = z.infer<typeof createUserSchema>;

interface CreateUserModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onUserCreated: (id: string) => Promise<unknown>;
}

export const CreateUserModal = ({
  open,
  onOpenChange,
  onUserCreated,
}: CreateUserModalProps) => {
  const { toast } = useToast();
  const [tenantId, setTenantId] = useState<string | undefined>(undefined);

  const createUserMutation = useRegisterAuthRegisterPost();

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors },
    reset,
  } = useForm<CreateUserFormData>({
    resolver: zodResolver(createUserSchema),
    defaultValues: {
      tenant_id: "",
    },
  });

  const onSubmit = async (data: CreateUserFormData) => {
    createUserMutation.mutate(
      {
        data: {
          name: data.name,
          email: data.email,
          password: data.password,
          tenant_id: data.tenant_id,
          is_admin: false,
          is_superadmin: false,
        },
      },
      {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        onSuccess: async (response: any) => {
          // ✅ Бэкенд возвращает созданный объект. Берём из него ID.
          // Используем 'any', так как типы Orval могут быть сложными, но 'id' там точно есть.
          const newId = response?.id;
          console.log("🔍 ПОЛНЫЙ ОТВЕТ БЕКЕНДА ПРИ СОЗДАНИИ:", response);
          if (!newId) {
            toast({
              variant: "destructive",
              title: "Ошибка",
              description: "Не удалось получить ID созданного пользователя",
            });
            return;
          }

          // ✅ Передаём этот ID наверх, в AdminUsersPage
          await onUserCreated(newId);

          // Сбрасываем форму и закрываем модалку
          reset();
          setTenantId(undefined);
          onOpenChange(false);
        },
        // onError: (error: unknown) => {
        //   let message = "Ошибка создания пользователя";

        //   if (error && typeof error === "object" && "response" in error) {
        //     const response = (
        //       error as { response?: { data?: { detail?: string } } }
        //     ).response;
        //     if (response?.data?.detail) {
        //       message = response.data.detail;
        //     }
        //   }

        //   toast({
        //     variant: "destructive",
        //     title: "Ошибка",
        //     description: message,
        //   });
        // },
        onError: (error: unknown) => {
          let message = "Ошибка создания пользователя";
          if (error && typeof error === "object" && "response" in error) {
            const response = (
              error as { response?: { data?: { detail?: string } } }
            ).response;
            // if (response?.data?.detail) {
            //   message = details[0].msg || message;
            // }
            
            // ✅ Парсим специфичный формат ошибок FastAPI (422 Unprocessable Entity)
            if (response?.data?.detail) {
              const details = response.data.detail;
              if (Array.isArray(details) && details.length > 0) {
                message = details[0].msg || message; // Берем первое сообщение (наш текст про email)
              } else if (typeof details === 'string') {
                message = details;
              }
            } else if (error && typeof error === "object" && "message" in error) {
              message = String(error.message);
            }
          }


          toast({
            variant: "destructive",
            title: "Ошибка валидации",
            description: message,
          });
        },
      },
    );
  };

  const handleClose = (open: boolean) => {
    if (!open) {
      reset();
      setTenantId(undefined);
    }
    onOpenChange(open);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Создание пользователя</DialogTitle>
          <DialogDescription>
            Зарегистрируйте нового пользователя в системе
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="create-name">Имя</Label>
            <Input id="create-name" {...register("name")} />
            {errors.name && (
              <p className="text-sm text-destructive">{errors.name.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="create-email">Email</Label>
            <Input id="create-email" type="email" {...register("email")} />
            {errors.email && (
              <p className="text-sm text-destructive">{errors.email.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="create-password">Пароль</Label>
            <Input
              id="create-password"
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
            <ReferenceSelect
              fetchFn={async () => {
                const tenants = await getTenantsTenantsGet({
                  active_only: true,
                });
                return tenants || [];
              }}
              queryKey={["tenants", "active"]}
              value={tenantId}
              onValueChange={(value) => {
                setTenantId(value);
                setValue("tenant_id", value, { shouldValidate: true });
              }}
              placeholder="Выберите организацию"
            />
            {/* Скрытое поле для react-hook-form */}
            <input
              type="hidden"
              {...register("tenant_id")}
              value={tenantId || ""}
            />
            {errors.tenant_id && (
              <p className="text-sm text-destructive">
                {errors.tenant_id.message}
              </p>
            )}
          </div>

          <DialogFooter className="gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => handleClose(false)}
            >
              Отмена
            </Button>
            <Button type="submit" disabled={createUserMutation.isPending}>
              {createUserMutation.isPending ? "Создание..." : "Создать"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};
