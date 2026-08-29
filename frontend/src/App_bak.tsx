import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { HomePage } from "@/core/HomePage";
import { RegisterPage } from "@/core/auth/RegisterPage";
import { LoginPage } from "@/core/LoginPage";
import { AppLayout } from "@/core/AppLayout";
import { ProfilePage } from "@/core/ProfilePage";
import { ProtectedRoute } from "@/core/ProtectedRoute";
import { AdminPage } from "@/core/admin/AdminPage";
import { SuperAdminPage } from "@/core/admin/SuperAdminPage";

// Создаем клиент TanStack Query один раз для всего приложения
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          {/* Страницы БЕЗ Layout (авторизация) */}
          <Route path="/auth/login" element={<LoginPage />} />
          <Route path="/auth/register" element={<RegisterPage />} />
                      {/* Админ-панель: только для admin или superadmin */}
          <Route 
            path="/admin" 
            element={
              <ProtectedRoute requiredRole="admin">
                <AdminPage />
              </ProtectedRoute>
            } 
          />
            
          {/* Супер-админ панель: только для superadmin */}
          <Route 
            path="/superadmin" 
            element={
              <ProtectedRoute requiredRole="superadmin">
                <SuperAdminPage />
              </ProtectedRoute>
            } 
          />
          {/* Страницы С Layout (все остальные) */}
          <Route element={<AppLayout />}>
            <Route path="/" element={<HomePage />} />
            <Route path="/profile" element={<ProfilePage />} />
            {/* Сюда позже добавим /profile и другие защищенные страницы */}
          </Route>
          
          {/* Fallback */}
          <Route path="*" element={<HomePage />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;