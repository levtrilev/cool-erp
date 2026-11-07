import { createContext } from "react";

// ============================================================
// ТИПЫ
// ============================================================
export type Theme = "light" | "dark" | "system";
export type ResolvedTheme = "light" | "dark";

/**
 * Идентификатор палитры тёмной темы.
 * "default" — базовый блок .dark без переопределений.
 * Остальные — классы .dark.palette-<id> в index.css.
 */
export type ThemePalette =
  | "default"
  | "onedark"
  | "nord"
  | "ghdimmed"
  | "catppuccin"
  | "solarized";

export interface ThemeContextValue {
  theme: Theme;
  resolvedTheme: ResolvedTheme;
  palette: ThemePalette;
  setTheme: (theme: Theme) => void;
  setPalette: (palette: ThemePalette) => void;
}

// ============================================================
// КОНСТАНТЫ И ХЕЛПЕРЫ (без компонентов — безопасно для Fast Refresh)
// ============================================================
export const THEME_STORAGE_KEY = "cool-erp-theme";
export const PALETTE_STORAGE_KEY = "cool-erp-palette";

/** Реестр палитр для меню переключения. */
export const THEME_PALETTES: ReadonlyArray<{
  id: ThemePalette;
  label: string;
  hint: string;
}> = [
  { id: "default", label: "Стандартная", hint: "Базовая тёмная палитра" },
  { id: "onedark", label: "One Dark", hint: "Стиль Atom / VS Code" },
  { id: "nord", label: "Nord", hint: "Холодная арктическая" },
  { id: "ghdimmed", label: "GitHub Dimmed", hint: "Средний контраст" },
  { id: "catppuccin", label: "Catppuccin Mocha", hint: "Тёплая пастельная" },
  { id: "solarized", label: "Solarized", hint: "Низкий контраст, мягкая" },
];

export const getSystemTheme = (): ResolvedTheme =>
  window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";

export const getInitialTheme = (): Theme => {
  const stored = localStorage.getItem(THEME_STORAGE_KEY);
  if (stored === "light" || stored === "dark" || stored === "system") {
    return stored;
  }
  return "system";
};

/** Безопасное чтение палитры: неизвестное значение → "default". */
export const getInitialPalette = (): ThemePalette => {
  const stored = localStorage.getItem(PALETTE_STORAGE_KEY);
  const found = THEME_PALETTES.find((p) => p.id === stored);
  return found ? found.id : "default";
};

export const ThemeContext = createContext<ThemeContextValue | undefined>(
  undefined,
);