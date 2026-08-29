import { useEffect } from "react";
import { useForm } from "react-hook-form";
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
import { useUpdateUserAuthUserIdPut } from "@/api/generated/authentication/authentication";

// Схема валидации
const editUserSchema = z.object({
  name: z.string().min(2, "Имя должно содержать минимум 2 символа"),
  email: z.string().email("Некорректный email"),
  password: z.string().min(8, "Пароль должен содержать минимум 8 символов").optional().or(z.literal("")),
});

type EditUserFormData = z.infer<typeof editUserSchema>;

// ✅ Определяем тип через Zod-схему (как обсуждали)
import { readUsersAuthGetResponse } from "@/api/generated/zod/authentication/authentication.schema";
type UserResponseSchema = z.infer<typeof readUsersAuthGetResponse>["items"][number];

interface EditUserModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  user: UserResponseSchema | null;
  onUserUpdated: () => void; // ✅ Колбэк для обновления списка
}

export const EditUserModal = ({ open, onOpenChange, user, onUserUpdated }: EditUserModalProps) => {
  const { toast } = useToast();
  const updateUserMutation = useUpdateUserAuthUserIdPut();

  const {
    register,
    handleSubmit,
    formState: { errors, isDirty },
    reset,
  } = useForm<EditUserFormData>({
    resolver: zodResolver(editUserSchema),
    values: {
      name: user?.name || "",
      email: user?.email || "",
      password: "",
    },
  });

  useEffect(() => {
    if (open && user) {
      reset({
        name: user.name,
        email: user.email,
        password: "",
      });
    }
  }, [open, user, reset]);

  const onSubmit = (data: EditUserFormData) => {
    if (!user?.id) return;

    const updateData = {
      name: data.name,
      email: data.email,
      ...(data.password ? { password: data.password } : {}),
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

          // ✅ Вызываем колбэк для обновления списка
          await onUserUpdated();

          onOpenChange(false);
        },
        onError: (error: unknown) => {
          let message = "Ошибка обновления пользователя";

          if (error && typeof error === "object" && "response" in error) {
            const response = (error as { response?: { data?: { detail?: string } } }).response;
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
      }
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
            <Input id="edit-password" type="password" {...register("password")} />
            {errors.password && (
              <p className="text-sm text-destructive">{errors.password.message}</p>
            )}
          </div>

          <DialogFooter className="gap-2">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Отмена
            </Button>
            <Button type="submit" disabled={updateUserMutation.isPending || !isDirty}>
              {updateUserMutation.isPending ? "Сохранение..." : "Сохранить"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};