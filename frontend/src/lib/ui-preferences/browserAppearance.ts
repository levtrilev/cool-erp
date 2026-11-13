// frontend/src/lib/ui-preferences/browserAppearance.ts
import { ThemePreferenceSchemaMode } from "@/api/generated/coolERP.schemas";
import {
  normalizeDarkPalette,
  normalizeLightPalette,
  type UiThemePreference,
} from "./themePalettes";
import type { NavigationLayout } from "./types";
import type { ResolvedTheme } from "./useSystemTheme";

export type { ResolvedTheme } from "./useSystemTheme";

export const THEME_COOKIE = "cool-erp-theme";
export const LIGHT_PALETTE_COOKIE = "cool-erp-light-palette";
export const DARK_PALETTE_COOKIE = "cool-erp-dark-palette";
export const NAV_LAYOUT_COOKIE = "cool-erp-nav-layout";

const COOKIE_MAX_AGE = 60 * 60 * 24 * 365;
const PALETTE_CLASS_PREFIX = "palette-";

/** Классы палитр, известные проекту; снимаются перед установкой активного. */
const KNOWN_PALETTE_CLASSES: readonly string[] = [
  "palette-sepia",
  "palette-onedark",
  "palette-nord",
  "palette-ghdimmed",
  "palette-catppuccin",
  "palette-solarized",
];

/** Разрешение режима в конкретную тему. Чистая функция, без обращения к DOM. */
export const resolveTheme = (
  mode: UiThemePreference["mode"],
  systemTheme: ResolvedTheme,
): ResolvedTheme => {
  if (mode === ThemePreferenceSchemaMode.dark) return "dark";
  if (mode === ThemePreferenceSchemaMode.light) return "light";
  return systemTheme;
};

const writeCookie = (name: string, value: string): void => {
  document.cookie = `${name}=${encodeURIComponent(value)}; path=/; max-age=${COOKIE_MAX_AGE}; samesite=lax`;
};

const readCookie = (name: string): string | null => {
  if (typeof document === "undefined") return null;
  const prefix: string = `${name}=`;
  const row: string | undefined = document.cookie
    .split("; ")
    .find((item) => item.startsWith(prefix));
  return row === undefined ? null : decodeURIComponent(row.slice(prefix.length));
};

/**
 * Применение темы и палитры к документу. ЕДИНСТВЕННЫЙ писатель оформления.
 *
 * Визуальный контракт палитр в index.css — КЛАССЫ:
 *   светлая: .palette-sepia
 *   тёмная:  .dark.palette-nord / .dark.palette-onedark / …
 * Поэтому снимаются все известные классы палитр и ставится активный.
 * Data-атрибуты — машиночитаемое дублирование состояния (отладка, будущие
 * селекторы), на цвета они не влияют.
 */
export const applyTheme = (
  theme: UiThemePreference,
  systemTheme: ResolvedTheme,
): void => {
  const resolved: ResolvedTheme = resolveTheme(theme.mode, systemTheme);
  const activePalette: string =
    resolved === "dark" ? theme.darkPalette : theme.lightPalette;

  const root: HTMLElement = document.documentElement;
  root.classList.toggle("dark", resolved === "dark");

  for (const paletteClass of KNOWN_PALETTE_CLASSES) {
    root.classList.remove(paletteClass);
  }
  if (activePalette !== "default") {
    root.classList.add(PALETTE_CLASS_PREFIX + activePalette);
  }

  root.dataset.palette = activePalette;
  root.dataset.lightPalette = theme.lightPalette;
  root.dataset.darkPalette = theme.darkPalette;
  root.style.colorScheme = resolved;

  writeCookie(THEME_COOKIE, resolved);
  writeCookie(LIGHT_PALETTE_COOKIE, theme.lightPalette);
  writeCookie(DARK_PALETTE_COOKIE, theme.darkPalette);
};

export const applyNavigationLayout = (layout: NavigationLayout): void => {
  document.documentElement.dataset.navLayout = layout;
  writeCookie(NAV_LAYOUT_COOKIE, layout);
};

/**
 * Оформление для первого кадра, до ответа сервера.
 * Читает ТОЛЬКО cookie: миграция из legacy-localStorage выполняется один раз
 * inline-скриптом в index.html, который затем очищает старые ключи.
 */
export const readInitialAppearance = (): UiThemePreference => {
  const storedTheme: string | null = readCookie(THEME_COOKIE);
  const mode =
    storedTheme === "dark"
      ? ThemePreferenceSchemaMode.dark
      : storedTheme === "light"
        ? ThemePreferenceSchemaMode.light
        : ThemePreferenceSchemaMode.system;

  return {
    mode,
    lightPalette: normalizeLightPalette(readCookie(LIGHT_PALETTE_COOKIE)),
    darkPalette: normalizeDarkPalette(readCookie(DARK_PALETTE_COOKIE)),
  };
};

/** Последняя известная раскладка — для первого рендера до ответа сервера. */
export const readNavigationLayoutCookie = (): NavigationLayout | null => {
  const raw: string | null = readCookie(NAV_LAYOUT_COOKIE);
  if (raw === null) return null;
  return raw === "topbar" ? (raw as NavigationLayout) : raw === "sidebar" ? (raw as NavigationLayout) : null;
};