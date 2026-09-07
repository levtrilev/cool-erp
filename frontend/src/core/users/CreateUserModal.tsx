import { useEffect } from "react";
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
import { ReferenceSelect } from "@/lib/reusable/ReferenceSelect";

// ✅ Импортируем Orval-хуки
import { useRegisterUsersRegisterPost } from "@/api/generated/users/users";
import { readTenantsTenantsGet } from "@/api/generated/tenants/tenants";

// Схема валидации
const createUserSchema = z.object({
  name: z.string().min(2, "Имя должно содержать минимум 2 символа"),
  email: z.string().email("Некорректный email"),
  password: z.string().min(8, "Пароль должен содержать минимум 8 символов"),
  tenant_id: z.string().min(1, "Выберите организацию").uuid("Некорректный ID организации"),
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
  const createUserMutation = useRegisterUsersRegisterPost();

  const {
    register,
    handleSubmit,
    control, // ✅ Добавляем control для Controller
    formState: { errors },
    reset,
  } = useForm<CreateUserFormData>({
    resolver: zodResolver(createUserSchema),
    defaultValues: {
      name: "",
      email: "",
      password: "",
      tenant_id: "", // ✅ Строка по умолчанию
    },
  });

  // ✅ Сбрасываем форму при закрытии модалки
  useEffect(() => {
    if (!open) {
      reset();
    }
  }, [open, reset]);

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
        onSuccess: async (response: unknown) => {
          // ✅ Безопасное извлечение ID из ответа
          const newId = response && typeof response === "object" && "id" in response 
            ? (response as { id: string }).id 
            : undefined;

          if (!newId) {
            toast({
              variant: "destructive",
              title: "Ошибка",
              description: "Не удалось получить ID созданного пользователя",
            });
            return;
          }

          // ✅ Передаём ID наверх
          await onUserCreated(newId);

          // Сбрасываем форму и закрываем модалку
          reset();
          onOpenChange(false);
        },
        onError: (error: unknown) => {
          let message = "Ошибка создания пользователя";
          
          if (error && typeof error === "object" && "response" in error) {
            const response = (error as { response?: { data?: { detail?: unknown } } }).response;
            
            // ✅ Парсим специфичный формат ошибок FastAPI (422 Unprocessable Entity)
            if (response?.data?.detail) {
              const details = response.data.detail;
              if (Array.isArray(details) && details.length > 0) {
                message = (details[0] as { msg?: string }).msg || message;
              } else if (typeof details === "string") {
                message = details;
              }
            } else if ("message" in error) {
              message = String((error as { message: string }).message);
            }
          }

          toast({
            variant: "destructive",
            title: "Ошибка валидации",
            description: message,
          });
        },
      }
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
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
            
            {/* ✅ Controller связывает ReferenceSelect с формой напрямую */}
            <Controller
              name="tenant_id"
              control={control}
              render={({ field }) => (
                <ReferenceSelect
                  fetchFn={async (params) => {
                    const response = await readTenantsTenantsGet(params);
                    // ✅ Адаптируем ответ под формат ReferenceSelect
                    return {
                      items: response?.items ?? [],
                      total: response?.total ?? 0,
                    };
                  }}
                  queryKey={["tenants", "active"]}
                  value={field.value || ""}
                  onValueChange={field.onChange}
                  placeholder="Выберите организацию"
                  heading="Выберите организацию" // ✅ Опционально: заголовок окна
                  columns={[{ column: "description", label: "Описание" }]}
                />
              )}
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
              onClick={() => onOpenChange(false)}
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