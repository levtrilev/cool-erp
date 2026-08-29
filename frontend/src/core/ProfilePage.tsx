import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { CheckCircle, AlertCircle } from "lucide-react";

// Импортируем сгенерированные хуки
import { 
  useGetUserAuthUserGet, 
  useUpdateUserAuthUserIdPut 
} from "@/api/generated/authentication/authentication";

// Схема валидации формы
const profileSchema = z.object({
  name: z.string().min(2, "Имя должно содержать минимум 2 символа"),
  email: z.string().email("Некорректный email"),
  password: z.string().min(8, "Пароль должен содержать минимум 8 символов").optional().or(z.literal("")),
});

type ProfileFormData = z.infer<typeof profileSchema>;

export const ProfilePage = () => {
  const navigate = useNavigate();
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Получаем данные текущего пользователя
  const { data: userData, isLoading: isLoadingUser } = useGetUserAuthUserGet();
  
  // Хук для обновления пользователя
  const updateUserMutation = useUpdateUserAuthUserIdPut();

  // Инициализируем форму с данными пользователя
  const {
    register,
    handleSubmit,
    formState: { errors, isDirty },
    reset,
  } = useForm<ProfileFormData>({
    resolver: zodResolver(profileSchema),
    values: {
      name: userData?.data?.name || "",
      email: userData?.data?.email || "",
      password: "",
    },
  });

  const onSubmit = (data: ProfileFormData) => {
    if (!userData?.data?.id) {
      setErrorMessage("Не удалось получить ID пользователя");
      return;
    }

    setSuccessMessage(null);
    setErrorMessage(null);

    // Готовим данные для отправки (убираем пустой пароль)
    const updateData = {
      name: data.name,
      email: data.email,
      ...(data.password ? { password: data.password } : {}),
    };

    updateUserMutation.mutate(
      {
        userId: userData.data.id,
        data: updateData,
      },
      {
        onSuccess: () => {
          setSuccessMessage("Профиль успешно обновлен");
          reset({
            name: data.name,
            email: data.email,
            password: "",
          });
        },
        onError: (error: unknown) => {
        // Безопасное извлечение сообщения об ошибке
        let message = "Ошибка обновления профиля";
        
        if (error && typeof error === 'object' && 'response' in error) {
            const response = (error as { response?: { data?: { detail?: string } } }).response;
            if (response?.data?.detail) {
            message = response.data.detail;
            }
        }
        
        setErrorMessage(message);
        },
      }
    );
  };

  if (isLoadingUser) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="text-muted-foreground animate-pulse">Загрузка профиля...</div>
      </div>
    );
  }

  if (!userData?.data) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>Не удалось загрузить данные профиля</AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-2xl">
      <Card>
        <CardHeader>
          <CardTitle className="text-2xl">Мой профиль</CardTitle>
          <CardDescription>
            Обновите информацию о вашем аккаунте
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            {/* Уведомления */}
            {successMessage && (
              <Alert>
                <CheckCircle className="h-4 w-4" />
                <AlertDescription>{successMessage}</AlertDescription>
              </Alert>
            )}
            {errorMessage && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{errorMessage}</AlertDescription>
              </Alert>
            )}

            {/* Имя */}
            <div className="space-y-2">
              <Label htmlFor="name">Имя</Label>
              <Input
                id="name"
                type="text"
                placeholder="Введите ваше имя"
                {...register("name")}
              />
              {errors.name && (
                <p className="text-sm text-destructive">{errors.name.message}</p>
              )}
            </div>

            {/* Email */}
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="your@email.com"
                {...register("email")}
              />
              {errors.email && (
                <p className="text-sm text-destructive">{errors.email.message}</p>
              )}
            </div>

            {/* Пароль */}
            <div className="space-y-2">
              <Label htmlFor="password">
                Новый пароль <span className="text-muted-foreground text-xs">(оставьте пустым, если не хотите менять)</span>
              </Label>
              <Input
                id="password"
                type="password"
                placeholder="••••••••"
                {...register("password")}
              />
              {errors.password && (
                <p className="text-sm text-destructive">{errors.password.message}</p>
              )}
            </div>

            {/* Информация об аккаунте */}
            <div className="rounded-lg bg-muted p-4 space-y-2">
              <h3 className="font-semibold text-sm">Информация об аккаунте</h3>
              <div className="text-sm space-y-1">
                <p>
                  <span className="text-muted-foreground">ID:</span>{" "}
                  <span className="font-mono text-xs">{userData.data.id}</span>
                </p>
                <p>
                  <span className="text-muted-foreground">Tenant ID:</span>{" "}
                  <span className="font-mono text-xs">{userData.data.tenant_id}</span>
                </p>
                <p>
                  <span className="text-muted-foreground">Роль:</span>{" "}
                  {userData.data.is_superadmin
                    ? "Супер-администратор"
                    : userData.data.is_admin
                    ? "Администратор"
                    : "Пользователь"}
                </p>
              </div>
            </div>

            {/* Кнопки */}
            <div className="flex gap-4">
              <Button
                type="submit"
                disabled={updateUserMutation.isPending || !isDirty}
              >
                {updateUserMutation.isPending ? "Сохранение..." : "Сохранить изменения"}
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => navigate("/")}
              >
                Отмена
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
};