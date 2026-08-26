import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { HomePage } from "@/core/HomePage";
import { RegisterPage } from "@/core/auth/RegisterPage";

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
          {/* Главная страница */}
          <Route path="/" element={<HomePage />} />
          
          {/* Страница регистрации */}
          <Route path="/auth/register" element={<RegisterPage />} />
          
          {/* Если путь не найден, показываем главную */}
          <Route path="*" element={<HomePage />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;