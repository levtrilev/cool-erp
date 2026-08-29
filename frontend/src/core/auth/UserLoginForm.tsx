import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { useNavigate, Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { AxiosError } from "axios";

// ⚠️ ЗАМЕНИТЕ ЭТИ ИМЕНА НА ТЕ, ЧТО СГЕНЕРИРОВАЛ ORVAL
import { loginAuthLoginPostBody } from "@/api/generated/zod/authentication/authentication.schema"; 
import { useLoginAuthLoginPost } from "@/api/generated/authentication/authentication";

type UserLoginFormValues = z.infer<typeof loginAuthLoginPostBody>;

export const UserLoginForm = () => {
  const navigate = useNavigate();
  
  const form = useForm<UserLoginFormValues>({
    resolver: zodResolver(loginAuthLoginPostBody),
    defaultValues: {
      email: "",
      password: "",
    },
  });

  const loginMutation = useLoginAuthLoginPost();

  const onSubmit = (data: UserLoginFormValues) => {
    loginMutation.mutate(
      { data },
      {
        onSuccess: () => {
          console.log("Успешный вход! Куки установлены.");
          navigate("/");
        },
        onError: (error) => {
          if (error instanceof AxiosError && error.response?.status === 401) {
            form.setError("root", {
              type: "server",
              message: "Неверный email или пароль",
            });
          } else {
            form.setError("root", {
              type: "server",
              message: "Произошла ошибка при входе. Попробуйте позже.",
            });
          }
        },
      }
    );
  };

  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <CardTitle>Вход в систему</CardTitle>
        <CardDescription>Введите свои учетные данные для доступа</CardDescription>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            
            {form.formState.errors.root && (
              <div className="p-3 bg-destructive/10 text-destructive text-sm rounded-md border border-destructive/20">
                {form.formState.errors.root.message}
              </div>
            )}

            <FormField
              control={form.control}
              name="email"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Email</FormLabel>
                  <FormControl>
                    <Input type="email" placeholder="you@example.com" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="password"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Пароль</FormLabel>
                  <FormControl>
                    <Input type="password" placeholder="••••••••" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <Button type="submit" className="w-full" disabled={loginMutation.isPending}>
              {loginMutation.isPending ? "Вход..." : "Войти"}
            </Button>

            <div className="text-center text-sm text-muted-foreground">
              Нет аккаунта?{" "}
              <Link to="/auth/register" className="text-primary hover:underline">
                Зарегистрироваться
              </Link>
            </div>
            
          </form>
        </Form>
      </CardContent>
    </Card>
  );
};