import axios from "axios";
import type {
  AxiosError,
  AxiosRequestConfig,
  AxiosResponse,
} from "axios";

export const AXIOS_INSTANCE = axios.create({
  baseURL: "http://localhost:8000",
  headers: {
    "Content-Type": "application/json",
  },
  withCredentials: true,
});

/**
 * Транспортный адаптер для Orval + React Query.
 *
 * Важно:
 * - снимается только обёртка AxiosResponse;
 * - бизнес-обёртка ApiResponse<T> сохраняется;
 * - компоненты должны читать:
 *   - одиночные объекты: data?.data?.field
 *   - списки: data?.data?.items / data?.data?.total
 */
export const customInstance = async <T>(
  config: AxiosRequestConfig,
  options?: AxiosRequestConfig,
): Promise<T> => {
  const response: AxiosResponse<T> = await AXIOS_INSTANCE.request<T>({
    ...config,
    ...options,
  });

  return response.data;
};

export type ErrorType<Error> = AxiosError<Error>;