// frontend/src/lib/ui-preferences/useThemePreference.ts
import { useCallback } from "react";
import { ThemePreferenceSchemaMode } from "@/api/generated/coolERP.schemas";
import { useUiPreferences } from "./useUiPreferences";
import { useSystemTheme, type ResolvedTheme } from "./useSystemTheme";
import { resolveTheme } from "./browserAppearance";
import {
  toApiThemePreference,
  type DarkPaletteId,
  type LightPaletteId,
  type ThemeMode,
  type UiThemePreference,
} from "./themePalettes";

export interface UseThemePreferenceResult {
  mode: ThemeMode;
  /** Тема, применённая к DOM с учётом режима «Как в системе». */
  resolvedTheme: ResolvedTheme;
  lightPalette: LightPaletteId;
  darkPalette: DarkPaletteId;
  setMode: (mode: ThemeMode) => void;
  /** Выбор светлой палитры одновременно включает светлую тему. */
  setLightPalette: (palette: LightPaletteId) => void;
  /** Выбор тёмной палитры одновременно включает тёмную тему. */
  setDarkPalette: (palette: DarkPaletteId) => void;
  isRestored: boolean;
}

/**
 * Тема и палитры из серверных настроек пользователя.
 * Единственный источник истины — БД; localStorage используется только
 * как резерв для первого кадра при миграции со старой схемы.
 * Каждое действие отправляет ПОЛНУЮ секцию theme и пишется немедленно.
 */
export const useThemePreference = (): UseThemePreferenceResult => {
  const { preferences, isRestored, patchImmediate } = useUiPreferences();
  const systemTheme: ResolvedTheme = useSystemTheme();
  const theme: UiThemePreference = preferences.theme;

  const setMode = useCallback(
    (mode: ThemeMode): void => {
      patchImmediate({ theme: toApiThemePreference({ ...theme, mode }) });
    },
    [patchImmediate, theme],
  );

  const setLightPalette = useCallback(
    (palette: LightPaletteId): void => {
      patchImmediate({
        theme: toApiThemePreference({
          ...theme,
          mode: ThemePreferenceSchemaMode.light,
          lightPalette: palette,
        }),
      });
    },
    [patchImmediate, theme],
  );

  const setDarkPalette = useCallback(
    (palette: DarkPaletteId): void => {
      patchImmediate({
        theme: toApiThemePreference({
          ...theme,
          mode: ThemePreferenceSchemaMode.dark,
          darkPalette: palette,
        }),
      });
    },
    [patchImmediate, theme],
  );

  return {
    mode: theme.mode,
    resolvedTheme: resolveTheme(theme.mode, systemTheme),
    lightPalette: theme.lightPalette,
    darkPalette: theme.darkPalette,
    setMode,
    setLightPalette,
    setDarkPalette,
    isRestored,
  };
};