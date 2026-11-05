// import type { UseQueryOptions } from "@tanstack/react-query";

/**
 * Единые опции запроса текущей сессии.
 * staleTime/gcTime = Infinity: повторные монтирования компонентов
 * НЕ вызывают новых запросов /auth/user.
 * Инвалидация выполняется явно: queryClient.clear() при login/logout.
 */
export const AUTH_USER_QUERY_OPTIONS = {
  query: {
    retry: false,
    staleTime: Number.POSITIVE_INFINITY,
    gcTime: Number.POSITIVE_INFINITY,
    refetchOnMount: false,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  },
} as const;