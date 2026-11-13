// frontend/src/lib/ui-preferences/uiPreferencesContext.ts
import { createContext } from "react";
import type { UiPreferencesPatchSchema } from "@/api/generated/coolERP.schemas";
import type { UiPreferences } from "./types";

export interface UiPreferencesContextValue {
  /** Нормализованные настройки: theme, navigation и tables заполнены всегда. */
  preferences: UiPreferences;
  /** true, когда настройки получены с сервера и применены. */
  isRestored: boolean;
  /** Оптимистичное обновление + отложенная запись (таблицы, поиск, страницы). */
  patch: (patch: UiPreferencesPatchSchema) => void;
  /**
   * Оптимистичное обновление + НЕМЕДЛЕННАЯ запись без дебаунса.
   * Для дискретных действий (тема, раскладка): значение не должно
   * потеряться, если пользователь сразу закроет вкладку или выйдет.
   */
  patchImmediate: (patch: UiPreferencesPatchSchema) => void;
}

/**
 * Контекст создаётся в отдельном не-компонентном файле:
 * Fast Refresh требует, чтобы компонентный файл экспортировал только компоненты.
 */
export const UiPreferencesContext =
  createContext<UiPreferencesContextValue | null>(null);