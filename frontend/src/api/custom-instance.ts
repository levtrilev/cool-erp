import axios, { AxiosError, AxiosRequestConfig } from 'axios';

// Базовый инстанс axios для всех запросов к бэкенду
export const AXIOS_INSTANCE = axios.create({
  baseURL: 'http://localhost:8000', // URL вашего FastAPI приложения
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // <-- ОБЯЗАТЕЛЬНО для HttpOnly куки!
});

// Функция-обертка, которую ожидает Orval для интеграции с React Query.
// Используем AxiosRequestConfig вместо any для строгой типизации.
export const customInstance = async <T>(
  config: AxiosRequestConfig,
  options?: AxiosRequestConfig
): Promise<T> => {
  const response = await AXIOS_INSTANCE({
    ...config,
    ...options,
  });
  return response.data;
};

// Тип ошибки для React Query (используется Orval для типизации ошибок)
export type ErrorType<Error> = AxiosError<Error>;