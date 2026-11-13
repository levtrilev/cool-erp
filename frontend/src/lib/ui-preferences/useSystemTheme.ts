// frontend/src/lib/ui-preferences/useSystemTheme.ts
import { useSyncExternalStore } from "react";

/** Тема, реально применяемая к DOM: только светлая или тёмная. */
export type ResolvedTheme = "light" | "dark";

const MEDIA_QUERY = "(prefers-color-scheme: dark)";

const subscribe = (onStoreChange: () => void): (() => void) => {
  if (typeof window === "undefined") return () => undefined;
  const media = window.matchMedia(MEDIA_QUERY);
  media.addEventListener("change", onStoreChange);
  return () => media.removeEventListener("change", onStoreChange);
};

const getSnapshot = (): boolean =>
  typeof window !== "undefined" && window.matchMedia(MEDIA_QUERY).matches;

const getServerSnapshot = (): boolean => false;

/**
 * Реактивная тема ОС. Единый источник для провайдера (применение палитры)
 * и для useThemePreference (иконка переключателя) — без дублирования подписок.
 */
export const useSystemTheme = (): ResolvedTheme =>
  useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot)
    ? "dark"
    : "light";