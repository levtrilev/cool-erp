import { useState, useEffect } from "react";
import { Outlet, Link, useNavigate } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { TopNav } from "./TopNav";
import { cn } from "@/lib/utils";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { UserCircle, LogOut, Loader2 } from "lucide-react";
import {
  useGetUserAuthUserGet,
  useLogoutAuthLogoutPost,
} from "@/api/generated/authentication/authentication";
import { useQueryClient } from "@tanstack/react-query";

type LayoutPosition = "left" | "top";

const STORAGE_KEY = "layout-position";

/**
 * Ленивая инициализация позиции макета из localStorage.
 * Выполняется только один раз при первом рендере компонента.
 */
const getInitialPosition = (): LayoutPosition => {
  try {
    const saved = localStorage.getItem(STORAGE_KEY) as LayoutPosition | null;
    if (saved === "left" || saved === "top") {
      return saved;
    }
  } catch {
    // Игнорируем ошибки доступа к localStorage
  }
  return "left";
};

/**
 * Компонент переключения макета.
 * Вынесен за пределы AppLayout, чтобы избежать создания компонента во время рендера.
 */
interface PositionSwitcherProps {
  current: LayoutPosition;
  onChange: (position: LayoutPosition) => void;
}

const PositionSwitcher = ({ current, onChange }: PositionSwitcherProps) => (
  <div className="fixed bottom-4 right-4 bg-background border border-border rounded-lg shadow-lg p-2 z-50">
    <div className="flex items-center gap-2">
      <span className="text-xs text-muted-foreground mr-1">Меню:</span>
      <button
        onClick={() => onChange("left")}
        className={cn(
          "px-2 py-1 text-xs rounded transition-colors",
          current === "left"
            ? "bg-primary text-primary-foreground"
            : "hover:bg-accent",
        )}
      >
        Слева
      </button>
      <button
        onClick={() => onChange("top")}
        className={cn(
          "px-2 py-1 text-xs rounded transition-colors",
          current === "top"
            ? "bg-primary text-primary-foreground"
            : "hover:bg-accent",
        )}
      >
        Сверху
      </button>
    </div>
  </div>
);

/**
 * Компонент профиля пользователя с выходом.
 * Вынесен отдельно для переиспользования в разных макетах.
 */
const UserOnLayout = () => {
  const { data: user, isLoading } = useGetUserAuthUserGet();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const logoutMutation = useLogoutAuthLogoutPost();

  // const handleLogout = () => {
  //   logoutMutation.mutate(undefined, {
  //     onSuccess: async () => {
  //       // ✅ ПОЛНОСТЬЮ очищаем весь кэш React Query
  //       queryClient.clear();
  //       await new Promise((resolve) => setTimeout(resolve, 50));
  //       navigate("/", { replace: true });
  //     },
  //     onError: async () => {
  //       // Даже если бэкенд упал, очищаем кэш
  //       queryClient.clear();
  //       await new Promise((resolve) => setTimeout(resolve, 50));
  //       navigate("/", { replace: true });
  //     },
  //   });
  // };
  const handleLogout = () => {
    logoutMutation.mutate(undefined, {
      onSuccess: async () => {
        // ✅ Полностью очищаем кэш
        queryClient.clear();
        await new Promise((resolve) => setTimeout(resolve, 50));
        // ✅ Редирект сразу на логин, а не на "/"
        navigate("/auth/login", { replace: true });
      },
      onError: async () => {
        queryClient.clear();
        await new Promise((resolve) => setTimeout(resolve, 50));
        navigate("/auth/login", { replace: true });
      },
    });
  };
  
  // ✅ Показываем загрузку, пока получаем данные пользователя
  if (isLoading) {
    return (
      <div className="flex items-center gap-2 px-3">
        <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        <span className="text-sm text-muted-foreground">Загрузка...</span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-4">
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            className="relative h-10 w-auto px-3 justify-start gap-2"
          >
            <UserCircle className="h-5 w-5" />
            <span className="hidden md:inline-block font-medium">
              {user?.data?.email || "Пользователь"}
            </span>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-56">
          <DropdownMenuLabel className="font-normal">
            <div className="flex flex-col space-y-1">
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
  );
};

export const AppLayout = () => {
  const navigate = useNavigate();
  // const queryClient = useQueryClient();

  // ✅ Ленивая инициализация позиции макета
  const [layoutPosition, setLayoutPosition] =
    useState<LayoutPosition>(getInitialPosition);

  // ✅ Auth Guard: проверка сессии пользователя
  // const { data: user, isError: isAuthError, isLoading: isAuthLoading } =
  const { isError: isAuthError, isLoading: isAuthLoading } =
    useGetUserAuthUserGet();

  // ✅ Редирект на логин при ошибке авторизации (401)
  useEffect(() => {
    if (isAuthError) {
      navigate("/auth/login", { replace: true });
    }
  }, [isAuthError, navigate]);

  const handlePositionChange = (position: LayoutPosition) => {
    setLayoutPosition(position);
    try {
      localStorage.setItem(STORAGE_KEY, position);
    } catch {
      // Игнорируем ошибки записи
    }
  };

  // ✅ Показываем загрузку, пока проверяем авторизацию
  if (isAuthLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-muted-foreground animate-pulse flex items-center gap-2">
          <Loader2 className="h-5 w-5 animate-spin" />
          Проверка авторизации...
        </div>
      </div>
    );
  }

  // ✅ В этом блоке TypeScript знает, что layoutPosition === "top"
  if (layoutPosition === "top") {
    return (
      <div className="min-h-screen flex flex-col">
        <div className="border-b bg-card shadow-sm">
          <div className="container mx-auto px-4 h-12 flex items-center justify-between">
            <TopNav />
            <UserOnLayout />
          </div>
        </div>
        <main className="flex-1 p-6 overflow-auto">
          <Outlet />
        </main>
        <PositionSwitcher
          current={layoutPosition}
          onChange={handlePositionChange}
        />
        <footer className="border-t bg-background py-3 mt-auto">
          <div className="container mx-auto px-4 text-center text-xs text-muted-foreground">
            © 2026 Cool ERP. Все права защищены.
          </div>
        </footer>
      </div>
    );
  }

  // ✅ В этом блоке TypeScript автоматически сужает тип layoutPosition до "left"
  return (
    <div className="min-h-screen flex">
      <Sidebar />
      <div className="min-h-screen flex flex-col flex-1">
        <div className="border-b bg-card shadow-sm">
          <div className="container mx-auto px-4 h-12 flex items-center justify-end">
            <UserOnLayout />
          </div>
        </div>
        <main className="flex-1 p-6 overflow-auto">
          <Outlet />
        </main>
        <PositionSwitcher
          current={layoutPosition}
          onChange={handlePositionChange}
        />
        <footer className="border-t bg-background py-3 mt-auto">
          <div className="container mx-auto px-4 text-center text-xs text-muted-foreground">
            © 2026 Cool ERP. Все права защищены.
          </div>
        </footer>
      </div>
    </div>
  );
};
