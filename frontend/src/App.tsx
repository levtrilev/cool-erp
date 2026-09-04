import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AppLayout } from "@/core/AppLayout";
import { ProtectedRoute } from "@/core/auth/ProtectedRoute";

// Публичные страницы
import { PublicHomePage } from "@/core/PublicHomePage";
import { LoginPage } from "@/core/auth/LoginPage";

// Защищённые страницы
import { DashboardPage } from "@/core/pages/DashboardPage";
import { ProfilePage } from "@/core/users/ProfilePage";
import { AdminPage } from "@/core/pages/AdminPage";
import { SuperAdminPage } from "@/core/pages/SuperAdminPage";
import { Toaster } from "@/components/ui/toaster";
import { AdminUsersPage } from "@/core/users/AdminUsersPage";
import { AdminTenantsPage } from "@/core/tenants/AdminTenantsPage";
import { AdminSectionsPage } from "@/core/sections/AdminSectionsPage";

const queryClient = new QueryClient();

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          {/* === ПУБЛИЧНЫЕ РОУТЫ (без Layout) === */}
          <Route path="/" element={<PublicHomePage />} />
          <Route path="/auth/login" element={<LoginPage />} />
          {/* <Route path="/auth/register" element={<RegisterPage />} /> */}

          {/* === ЗАЩИЩЁННЫЕ РОУТЫ (с Layout) === */}
          <Route element={<AppLayout />}>
            {/* Dashboard — главная для залогиненных */}
            <Route path="/dashboard" element={<DashboardPage />} />

            {/* Профиль */}
            <Route path="/profile" element={<ProfilePage />} />

            {/* Админ-панель: только для admin/superadmin */}
            <Route
              path="/admin"
              element={
                <ProtectedRoute requiredRole="admin">
                  <AdminPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/users"
              element={
                <ProtectedRoute requiredRole="admin">
                  <AdminUsersPage />
                </ProtectedRoute>
              }
            />           
            <Route
              path="/admin/tenants"
              element={
                <ProtectedRoute requiredRole="admin">
                  <AdminTenantsPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/sections"
              element={
                <ProtectedRoute requiredRole="admin">
                  <AdminSectionsPage />
                </ProtectedRoute>
              }
            />
            {/* Супер-админ: только для superadmin */}
            <Route
              path="/superadmin"
              element={
                <ProtectedRoute requiredRole="superadmin">
                  <SuperAdminPage />
                </ProtectedRoute>
              }
            />

            {/* Сюда добавляйте сотни будущих страниц с RBAC */}
            {/* <Route element={<ProtectedRoute requiredRole="manager" />}>
              <Route path="/projects" element={<ProjectsPage />} />
            </Route> */}
          </Route>

          {/* Редирект для неизвестных путей */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
      <Toaster />
    </QueryClientProvider>
  );
}

export default App;
