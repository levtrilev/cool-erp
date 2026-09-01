import { Navigate, useLocation } from "react-router-dom";
import { useGetUserAuthUserGet } from "@/api/generated/authentication/authentication";

type RoleType = "admin" | "superadmin";

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredRole?: RoleType;
}

export const ProtectedRoute = ({ children, requiredRole }: ProtectedRouteProps) => {
  const location = useLocation();
  const { data: userData, isLoading, isError } = useGetUserAuthUserGet();

  // Показываем загрузку, пока проверяем сессию
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-muted-foreground animate-pulse">Проверка доступа...</div>
      </div>
    );
  }

  // Если сессия невалидна (401), редиректим на логин
  if (isError) {
    return <Navigate to="/auth/login" state={{ from: location }} replace />;
  }

  // Проверяем роль, если она требуется
  if (requiredRole) {
    const user = userData?.data;
    
    if (!user) {
      return <Navigate to="/auth/login" state={{ from: location }} replace />;
    }

    // Проверка ролей
    const hasAccess = 
      requiredRole === "admin" 
        ? user.is_admin || user.is_superadmin // Админ или супер-админ имеют доступ
        : requiredRole === "superadmin"
        ? user.is_superadmin // Только супер-админ
        : false;

    if (!hasAccess) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-background">
          <div className="text-center space-y-4">
            <h1 className="text-4xl font-bold text-destructive">403</h1>
            <p className="text-xl text-muted-foreground">
              Доступ запрещен
            </p>
            <p className="text-sm text-muted-foreground">
              У вас нет прав для просмотра этой страницы
            </p>
          </div>
        </div>
      );
    }
  }

  // Если все проверки пройдены, рендерим дочерний компонент
  return <>{children}</>;
};