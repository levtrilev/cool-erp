import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AppLayout } from "@/components/layout/AppLayout";
import { NotesPage } from "@/core/notes/NotesPage";
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
import { AdminRolesPage } from "@/core/roles/AdminRolesPage";
import { DomainsPage } from "@/core/domains/DomainsPage";
import { DoctypesPage } from "@/core/doctypes/DoctypesPage";
import { TagsPage } from "./core/tags/TagsPage";
import { GoodsPage } from "./modules/sales/goods/GoodsPage";
import { WarehousesPage } from "./modules/inventory/warehouses/WarehousesPage";
import { CompaniesPage } from "./modules/business_partners/CompaniesPage";
import { RegionsPage } from "./modules/sales/regions/RegionsPage";
import { RegisterPage } from "./core/users/RegisterPage";
// import { AuditPage } from "@/modules/audit/AuditPage";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // ✅ Умная логика retry: 401/403 — сразу отказ без повторных попыток
      retry: (failureCount, error) => {
        console.log("🔍 Retry check:", { failureCount, error });
        const status = (error as { response?: { status?: number } })
          ?.response?.status;
        if (status === 401 || status === 403) {
          return false; // Мгновенный отказ при потере авторизации
        }
        return failureCount < 2; // Для сетевых ошибок / 500 — 2 попытки
      },
      retryDelay: 200,
    },
    mutations: {
      retry: false, // Мутации никогда не ретраятся автоматически
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<AppLayout />}>
            <Route path="/notes" element={<NotesPage />} />
            <Route path="/sales/goods" element={<GoodsPage />} />
            <Route path="/inventory/warehouses" element={<WarehousesPage />} />
            <Route
              path="/business-partners/companies"
              element={<CompaniesPage />}
            />
            <Route path="/sales/regions" element={<RegionsPage />} />
            {/* Другие маршруты будут добавлены здесь */}
          </Route>

          {/* === ПУБЛИЧНЫЕ РОУТЫ (без Layout) === */}
          <Route path="/" element={<PublicHomePage />} />
          <Route path="/auth/login" element={<LoginPage />} />
          <Route path="/auth/register__" element={<RegisterPage />} />

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
              path="/admin/domains"
              element={
                <ProtectedRoute requiredRole="admin">
                  <DomainsPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/doctypes"
              element={
                <ProtectedRoute requiredRole="admin">
                  <DoctypesPage />
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
            <Route
              path="/admin/roles"
              element={
                <ProtectedRoute requiredRole="admin">
                  <AdminRolesPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/tags"
              element={
                <ProtectedRoute requiredRole="admin">
                  <TagsPage />
                </ProtectedRoute>
              }
            />
            {/* <Route
              path="/admin/audit"
              element={
                <ProtectedRoute requiredRole="admin">
                  <AuditPage />
                </ProtectedRoute>
              }
            /> */}
            {/* Супер-админ: только для superadmin */}
            <Route
              path="/superadmin"
              element={
                <ProtectedRoute requiredRole="superadmin">
                  <SuperAdminPage />
                </ProtectedRoute>
              }
            />
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