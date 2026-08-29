import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { HomePage } from "@/core/HomePage";
import { RegisterPage } from "@/core/auth/RegisterPage";
import { LoginPage } from "@/core/LoginPage";
import { AppLayout } from "./core/AppLayout";
import { ProfilePage } from "./core/ProfilePage";

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