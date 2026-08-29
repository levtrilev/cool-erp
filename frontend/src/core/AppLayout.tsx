import { Outlet, Link, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { UserCircle, LogOut } from "lucide-react";

import { useGetUserAuthUserGet } from "@/api/generated/authentication/authentication";
import { useLogoutAuthLogoutPost } from "@/api/generated/authentication/authentication";
import { useEffect } from "react";

export const AppLayout = () => {
  const navigate = useNavigate();

  // Запрашиваем данные пользователя.
  // data содержит ответ от сервера (имя, email и т.д.)
  const { data: user, isError, isLoading } = useGetUserAuthUserGet();

// ✅ ВРЕМЕННЫЙ ЛОГ ДЛЯ ДИАГНОСТИКИ
console.log("=== ДАННЫЕ ПОЛЬЗОВАТЕЛЯ ===", user);
console.log("Тип данных:", typeof user);
console.log("Ключи:", user ? Object.keys(user) : "нет данных");

  const logoutMutation = useLogoutAuthLogoutPost();

  // 2. Auth Guard: если сессия невалидна (401), редиректим на логин
  useEffect(() => {
    if (isError) {
      navigate("/auth/login", { replace: true });
    }
  }, [isError, navigate]);

  const handleLogout = () => {
    logoutMutation.mutate(
      undefined, // Пустой объект, так как у logout нет body
      {
        onSuccess: () => {
          console.log("Успешный выход");
          navigate("/auth/login");
        },
        onError: (error) => {
          console.error("Ошибка выхода:", error);
          // Даже при ошибке редиректим на логин
          navigate("/auth/login");
        },
      },
    );
  };

  // Показываем загрузку, пока проверяем сессию
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-muted-foreground animate-pulse">Проверка авторизации...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col bg-background">
      {/* Header */}
      <header className="border-b bg-card shadow-sm">
        <div className="container mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <Link to="/" className="text-xl font-bold text-primary">
              Cool ERP
            </Link>
            <nav className="hidden md:flex items-center gap-4">
              <Link
                to="/"
                className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
              >
                Главная
              </Link>
              {/* Сюда позже добавим пункты меню */}
            </nav>
          </div>

          {/* Правая часть: профиль и выход */}
          <div className="flex items-center gap-4">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="relative h-10 w-auto px-3 justify-start gap-2">
                  <UserCircle className="h-5 w-5" />
                  {/* ✅ ПОКАЗЫВАЕМ ИМЯ ПОЛЬЗОВАТЕЛЯ, если оно есть */}
                  <span className="hidden md:inline-block font-medium">
                    {user?.data?.email || "Пользователь"}
                  </span>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuLabel className="font-normal">
                  <div className="flex flex-col space-y-1">
                    {/* ✅ ПОКАЗЫВАЕМ ИМЯ И EMAIL В МЕНЮ */}
                    <p className="text-sm font-medium leading-none">
                      {user?.data?.name || "Пользователь"}
                    </p>
                    <p className="text-xs leading-none text-muted-foreground">
                      {user?.data?.email || "email@example.com"}
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
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 container mx-auto px-4 py-8">
        <Outlet /> {/* Здесь будет рендериться содержимое дочерних роутов */}
      </main>

      {/* Footer */}
      <footer className="border-t bg-card py-4">
        <div className="container mx-auto px-4 text-center text-sm text-muted-foreground">
          © 2026 Cool ERP. Все права защищены.
        </div>
      </footer>
    </div>
  );
};
