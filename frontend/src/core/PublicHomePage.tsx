import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { LoginModal } from "@/core/auth/LoginModal";
import { RegisterModal } from "@/core/auth/RegisterModal";
import { Shield, Users, Zap, UserCircle, LogOut } from "lucide-react";
import { useGetUserAuthUserGet } from "@/api/generated/authentication/authentication";
import { useLogoutAuthLogoutPost } from "@/api/generated/authentication/authentication";
import { useQueryClient } from "@tanstack/react-query";

export const PublicHomePage = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [loginOpen, setLoginOpen] = useState(false);
  const [registerOpen, setRegisterOpen] = useState(false);

  // Проверяем, залогинен ли пользователь
  const { data: userData, isError } = useGetUserAuthUserGet();
  const logoutMutation = useLogoutAuthLogoutPost();

  //   const handleLogout = () => {
  //     logoutMutation.mutate(undefined, {
  //       onSuccess: async () => {
  //         await queryClient.invalidateQueries({
  //           queryKey: ["getUserAuthUserGet"],
  //         });
  //         navigate("/", { replace: true });
  //       },
  //       onError: async () => {
  //         await queryClient.invalidateQueries({
  //           queryKey: ["getUserAuthUserGet"],
  //         });
  //         navigate("/", { replace: true });
  //       },
  //     });
  //   };
  const handleLogout = () => {
    logoutMutation.mutate(undefined, {
      onSuccess: async () => {
        // ✅ ПОЛНОСТЬЮ очищаем весь кэш React Query
        queryClient.clear();

        // Небольшая задержка, чтобы кэш гарантированно очистился
        await new Promise((resolve) => setTimeout(resolve, 50));

        navigate("/", { replace: true });
      },
      onError: async () => {
        // Даже если бэкенд упал, очищаем кэш
        queryClient.clear();

        await new Promise((resolve) => setTimeout(resolve, 50));

        navigate("/", { replace: true });
      },
    });
  };

  // ✅ По умолчанию считаем, что пользователь не залогинен.
  // Когда запрос завершится, React автоматически перерисует компонент с актуальными данными.
  const isLoggedIn = !!userData?.data && !isError;

  return (
    <div className="min-h-screen bg-gradient-to-br from-background to-muted">
      {/* Хедер */}
      <header className="border-b bg-background/80 backdrop-blur-sm sticky top-0 z-40">
        <div className="container mx-auto px-4 h-16 flex items-center justify-between">
          <div className="text-xl font-bold text-primary">Cool ERP</div>

          {/* ✅ Правая часть: профиль ИЛИ кнопки входа */}
          <div className="flex items-center gap-4">
            {isLoggedIn ? (
              // Пользователь залогинен — показываем профиль
              <>
                <Button variant="ghost" asChild>
                  <Link to="/dashboard">Панель управления</Link>
                </Button>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant="ghost"
                      className="relative h-10 w-auto px-3 justify-start gap-2"
                    >
                      <UserCircle className="h-5 w-5" />
                      <span className="hidden md:inline-block font-medium">
                        {userData?.data?.name || "Пользователь"}
                      </span>
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-56">
                    <DropdownMenuLabel className="font-normal">
                      <div className="flex flex-col space-y-1">
                        <p className="text-sm font-medium leading-none">
                          {userData?.data?.name || "Пользователь"}
                        </p>
                        <p className="text-xs leading-none text-muted-foreground">
                          {userData?.data?.email || "email@example.com"}
                        </p>
                      </div>
                    </DropdownMenuLabel>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem asChild>
                      <Link to="/profile" className="cursor-pointer">
                        Профиль
                      </Link>
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      onClick={handleLogout}
                      className="cursor-pointer text-destructive focus:text-destructive"
                    >
                      <LogOut className="mr-2 h-4 w-4" />
                      <span>Выйти</span>
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </>
            ) : (
              // Пользователь НЕ залогинен — показываем кнопки входа
              <>
                <Button variant="ghost" onClick={() => setLoginOpen(true)}>
                  Войти
                </Button>
                <Button onClick={() => setRegisterOpen(true)}>
                  Регистрация
                </Button>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Hero секция */}
      <main className="container mx-auto px-4 py-20">
        <div className="max-w-3xl mx-auto text-center space-y-8">
          <h1 className="text-5xl md:text-6xl font-bold tracking-tight">
            Добро пожаловать в <span className="text-primary">Cool ERP</span>
          </h1>
          <p className="text-xl text-muted-foreground">
            Современная платформа для управления вашими проектами и командами
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            {isLoggedIn ? (
              <Button size="lg" asChild>
                <Link to="/dashboard">Перейти в панель управления</Link>
              </Button>
            ) : (
              <>
                <Button size="lg" onClick={() => setRegisterOpen(true)}>
                  Начать бесплатно
                </Button>
                <Button
                  size="lg"
                  variant="outline"
                  onClick={() => setLoginOpen(true)}
                >
                  У меня есть аккаунт
                </Button>
              </>
            )}
          </div>
        </div>

        {/* Фичи */}
        <div className="grid md:grid-cols-3 gap-8 mt-20 max-w-5xl mx-auto">
          <div className="bg-card rounded-lg p-6 border shadow-sm">
            <Shield className="h-10 w-10 text-primary mb-4" />
            <h3 className="text-lg font-semibold mb-2">Безопасность</h3>
            <p className="text-sm text-muted-foreground">
              Защита данных на уровне предприятия с ролевой моделью доступа
            </p>
          </div>
          <div className="bg-card rounded-lg p-6 border shadow-sm">
            <Users className="h-10 w-10 text-primary mb-4" />
            <h3 className="text-lg font-semibold mb-2">Командная работа</h3>
            <p className="text-sm text-muted-foreground">
              Эффективное управление командами и проектами любого размера
            </p>
          </div>
          <div className="bg-card rounded-lg p-6 border shadow-sm">
            <Zap className="h-10 w-10 text-primary mb-4" />
            <h3 className="text-lg font-semibold mb-2">Производительность</h3>
            <p className="text-sm text-muted-foreground">
              Быстрый интерфейс и автоматизация рутинных задач
            </p>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t bg-background py-6 mt-20">
        <div className="container mx-auto px-4 text-center text-sm text-muted-foreground">
          © 2026 Cool ERP. Все права защищены.
        </div>
      </footer>

      {/* Модалки (показываются только если НЕ залогинен) */}
      {!isLoggedIn && (
        <>
          <LoginModal
            open={loginOpen}
            onOpenChange={setLoginOpen}
            onSwitchToRegister={() => {
              setLoginOpen(false);
              setRegisterOpen(true);
            }}
          />
          <RegisterModal
            open={registerOpen}
            onOpenChange={setRegisterOpen}
            onSwitchToLogin={() => {
              setRegisterOpen(false);
              setLoginOpen(true);
            }}
          />
        </>
      )}
    </div>
  );
};
