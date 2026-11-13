// frontend/src/components/layout/AppLayout.tsx
import { useEffect, useMemo } from "react";
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
  useGetCurrentUserAuthUserGet,
  useLogoutAuthLogoutPost,
} from "@/api/generated/authentication/authentication";
import { useQueryClient } from "@tanstack/react-query";
import { NavigationPreferenceSchemaLayout } from "@/api/generated/coolERP.schemas";
import { ThemeToggle } from "@/components/theme/ThemeToggle";
import { UiPreferencesProvider } from "@/lib/ui-preferences/UiPreferencesProvider";
import { useNavigationPreference } from "@/lib/ui-preferences/useNavigationPreference";
import { readNavigationLayoutCookie } from "@/lib/ui-preferences/browserAppearance";
import type { NavigationLayout } from "@/lib/ui-preferences/types";

interface PositionSwitcherProps {
  current: NavigationLayout;
  onChange: (layout: NavigationLayout) => void;
  disabled: boolean;
}

/** Переключатель раскладки меню. Пишет в серверные настройки пользователя. */
const PositionSwitcher = ({
  current,
  onChange,
  disabled,
}: PositionSwitcherProps) => (
  <div className="fixed bottom-4 right-4 bg-background border border-border rounded-lg shadow-lg p-2 z-50">
    <div className="flex items-center gap-2">
      <span className="text-xs text-muted-foreground mr-1">Меню:</span>
      <button
        type="button"
        disabled={disabled}
        onClick={() => onChange(NavigationPreferenceSchemaLayout.sidebar)}
        className={cn(
          "px-2 py-1 text-xs rounded transition-colors disabled:opacity-50 disabled:pointer-events-none",
          current === NavigationPreferenceSchemaLayout.sidebar
            ? "bg-primary text-primary-foreground"
            : "hover:bg-accent",
        )}
      >
        Слева
      </button>
      <button
        type="button"
        disabled={disabled}
        onClick={() => onChange(NavigationPreferenceSchemaLayout.topbar)}
        className={cn(
          "px-2 py-1 text-xs rounded transition-colors disabled:opacity-50 disabled:pointer-events-none",
          current === NavigationPreferenceSchemaLayout.topbar
            ? "bg-primary text-primary-foreground"
            : "hover:bg-accent",
        )}
      >
        Сверху
      </button>
    </div>
  </div>
);

/** Профиль пользователя с выходом. */
const UserOnLayout = () => {
  const { data: user, isLoading } = useGetCurrentUserAuthUserGet();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const logoutMutation = useLogoutAuthLogoutPost();

  const handleLogout = () => {
    logoutMutation.mutate(undefined, {
      onSuccess: async () => {
        // Настройки интерфейса НЕ удаляются: они хранятся в БД за пользователем.
        queryClient.clear();
        await new Promise((resolve) => setTimeout(resolve, 50));
        navigate("/auth/login", { replace: true });
      },
      onError: async () => {
        queryClient.clear();
        await new Promise((resolve) => setTimeout(resolve, 50));
        navigate("/auth/login", { replace: true });
      },
    });
  };

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

/**
 * Внутренний макет. Находится ВНУТРИ провайдера, поэтому и шапка
 * (ThemeToggle, PositionSwitcher), и страницы видят одни настройки.
 */
const AppLayoutInner = () => {
  const navigate = useNavigate();
  const { isError: isAuthError, isLoading: isAuthLoading } =
    useGetCurrentUserAuthUserGet();
  const { layout, setLayout, isRestored } = useNavigationPreference();

  // До ответа сервера — последнее известное значение из cookie,
  // чтобы раскладка не «прыгала» при перезагрузке страницы.
  const cookieLayout: NavigationLayout | null = useMemo(
    () => readNavigationLayoutCookie(),
    [],
  );
  const effectiveLayout: NavigationLayout = isRestored
    ? layout
    : (cookieLayout ?? NavigationPreferenceSchemaLayout.sidebar);

  useEffect(() => {
    if (isAuthError) {
      navigate("/", { replace: true });
    }
  }, [isAuthError, navigate]);

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

  const footer = (
    <footer className="border-t bg-background py-3 mt-auto">
      <div className="container mx-auto px-4 text-center text-xs text-muted-foreground">
        © 2026 Cool ERP. Все права защищены.
      </div>
    </footer>
  );

  if (effectiveLayout === NavigationPreferenceSchemaLayout.topbar) {
    return (
      <div className="min-h-screen flex flex-col">
        <div className="border-b bg-card shadow-sm">
          <div className="container mx-auto px-4 h-12 flex items-center justify-between">
            <TopNav />
            <ThemeToggle />
            <UserOnLayout />
          </div>
        </div>
        <main className="flex-1 p-6 overflow-auto">
          <Outlet />
        </main>
        <PositionSwitcher
          current={effectiveLayout}
          onChange={setLayout}
          disabled={!isRestored}
        />
        {footer}
      </div>
    );
  }

  return (
    <div className="min-h-screen flex">
      <Sidebar />
      <div className="min-h-screen flex flex-col flex-1">
        <div className="border-b bg-card shadow-sm">
          <div className="container mx-auto px-4 h-12 flex items-center justify-end">
            <ThemeToggle />
            <UserOnLayout />
          </div>
        </div>
        <main className="flex-1 p-6 overflow-auto">
          <Outlet />
        </main>
        <PositionSwitcher
          current={effectiveLayout}
          onChange={setLayout}
          disabled={!isRestored}
        />
        {footer}
      </div>
    </div>
  );
};

/**
 * Провайдер настроек — ЕДИНСТВЕННЫЙ экземпляр над всем макетом.
 * Раньше он оборачивал только <Outlet />, поэтому ThemeToggle в шапке
 * работал от отдельного источника и смена темы не сохранялась в БД.
 */
export const AppLayout = () => (
  <UiPreferencesProvider>
    <AppLayoutInner />
  </UiPreferencesProvider>
);