// frontend/src/lib/ui-preferences/themePalettes.ts
import {
  DARK_PALETTES,
  LIGHT_PALETTES,
  type DarkPalette,
  type LightPalette,
} from "@/components/theme/theme-context";
import {
  type ThemePreferenceSchema,
  type UiPreferencesResponseSchema,
} from "@/api/generated/coolERP.schemas";

type ThemePreference = NonNullable<UiPreferencesResponseSchema["theme"]>;

/** Режим темы: строковый enum Orval (номинальный тип). */
export type ThemeMode = NonNullable<ThemePreference["mode"]>;

/** Идентификаторы палитр — из единственного источника истины theme-context.ts. */
export type LightPaletteId = LightPalette;
export type DarkPaletteId = DarkPalette;

export interface UiThemePreference {
  mode: ThemeMode;
  lightPalette: LightPaletteId;
  darkPalette: DarkPaletteId;
}

export const DEFAULT_LIGHT_PALETTE: LightPaletteId = "default";
export const DEFAULT_DARK_PALETTE: DarkPaletteId = "default";

/** Невалидное или отсутствующее значение заменяется палитрой по умолчанию. */
export const normalizeLightPalette = (
  raw: string | null | undefined,
): LightPaletteId => {
  const found = LIGHT_PALETTES.find((palette) => palette.id === raw);
  return found === undefined ? DEFAULT_LIGHT_PALETTE : found.id;
};

export const normalizeDarkPalette = (
  raw: string | null | undefined,
): DarkPaletteId => {
  const found = DARK_PALETTES.find((palette) => palette.id === raw);
  return found === undefined ? DEFAULT_DARK_PALETTE : found.id;
};

export const normalizeThemePreference = (
  raw: UiPreferencesResponseSchema["theme"],
): UiThemePreference => ({
  mode: raw?.mode ?? ("system" as ThemeMode),
  lightPalette: normalizeLightPalette(raw?.light_palette),
  darkPalette: normalizeDarkPalette(raw?.dark_palette),
});

/**
 * Полный объект секции theme для PATCH.
 * Отправляются ВСЕ три поля: бэкенд заменяет секцию целиком,
 * поэтому неполный объект сбросил бы палитры к значениям по умолчанию.
 * Палитры уходят как строки: их id совпадают со значениями API.
 */
export const toApiThemePreference = (
  theme: UiThemePreference,
): ThemePreferenceSchema => ({
  mode: theme.mode,
  light_palette: theme.lightPalette,
  dark_palette: theme.darkPalette,
});

export { DARK_PALETTES, LIGHT_PALETTES };