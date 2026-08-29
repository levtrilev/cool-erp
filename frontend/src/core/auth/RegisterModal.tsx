import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { AlertCircle, CheckCircle } from "lucide-react";
import { useRegisterAuthRegisterPost } from "@/api/generated/authentication/authentication";

const registerSchema = z
  .object({
    name: z.string().min(2, "Имя должно содержать минимум 2 символа"),
    email: z.string().email("Некорректный email"),
    password: z.string().min(8, "Пароль должен содержать минимум 8 символов"),
    confirmPassword: z.string(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Пароли не совпадают",
    path: ["confirmPassword"],
  });

type RegisterFormData = z.infer<typeof registerSchema>;

interface RegisterModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSwitchToLogin: () => void;
}

export const RegisterModal = ({ open, onOpenChange, onSwitchToLogin }: RegisterModalProps) => {
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const registerMutation = useRegisterAuthRegisterPost();

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
  });

  const onSubmit = (data: RegisterFormData) => {
    setErrorMessage(null);
    setSuccessMessage(null);

    registerMutation.mutate(
    {
        data: {
        name: data.name,
        email: data.email,
        password: data.password,
        // Временно захардкодим tenant_id — потом заменим на выбор
        tenant_id: "00000000-0000-0000-0000-000000000001",
        is_admin: false,
        is_superadmin: false,
        },
    },
    {
        onSuccess: () => {
        setSuccessMessage("Регистрация успешна! Теперь войдите в систему.");
        reset();
        setTimeout(() => {
            onOpenChange(false);
            onSwitchToLogin();
        }, 1500);
        },
        onError: (error: unknown) => {
        let message = "Ошибка регистрации";
        
        if (error && typeof error === 'object' && 'response' in error) {
            const response = (error as { response?: { data?: { detail?: unknown } } }).response;
            const detail = response?.data?.detail;
            
            if (Array.isArray(detail)) {
            message = detail[0]?.msg || message;
            } else if (typeof detail === "string") {
            message = detail;
            }
        }
        
        setErrorMessage(message);
        },
    }
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Регистрация</DialogTitle>
          <DialogDescription>
            Создайте новый аккаунт в системе
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {errorMessage && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{errorMessage}</AlertDescription>
            </Alert>
          )}
          {successMessage && (
            <Alert>
              <CheckCircle className="h-4 w-4" />
              <AlertDescription>{successMessage}</AlertDescription>
            </Alert>
          )}

          <div className="space-y-2">
            <Label htmlFor="register-name">Имя</Label>
            <Input id="register-name" {...register("name")} />
            {errors.name && (
              <p className="text-sm text-destructive">{errors.name.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="register-email">Email</Label>
            <Input id="register-email" type="email" {...register("email")} />
            {errors.email && (
              <p className="text-sm text-destructive">{errors.email.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="register-password">Пароль</Label>
            <Input id="register-password" type="password" {...register("password")} />
            {errors.password && (
              <p className="text-sm text-destructive">{errors.password.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="register-confirm">Подтвердите пароль</Label>
            <Input id="register-confirm" type="password" {...register("confirmPassword")} />
            {errors.confirmPassword && (
              <p className="text-sm text-destructive">{errors.confirmPassword.message}</p>
            )}
          </div>

          <div className="flex flex-col gap-2">
            <Button type="submit" disabled={registerMutation.isPending} className="w-full">
              {registerMutation.isPending ? "Регистрация..." : "Зарегистрироваться"}
            </Button>
            <Button
              type="button"
              variant="link"
              onClick={() => {
                onOpenChange(false);
                onSwitchToLogin();
              }}
            >
              Уже есть аккаунт? Войти
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
};
