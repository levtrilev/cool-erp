// import { createContext } from "react";

// // ============================================================
// // ТИПЫ
// // ============================================================
// export type Theme = "light" | "dark" | "system";
// export type ResolvedTheme = "light" | "dark";

// /** Палитры светлой темы. "default" — базовый :root без переопределений. */
// export type LightPalette = "default" | "sepia";

// /** Палитры тёмной темы. "default" — базовый .dark без переопределений. */
// export type DarkPalette =
//   | "default"
//   | "onedark"
//   | "nord"
//   | "ghdimmed"
//   | "catppuccin"
//   | "solarized";

// export interface ThemeContextValue {
//   theme: Theme;
//   resolvedTheme: ResolvedTheme;
//   lightPalette: LightPalette;
//   darkPalette: DarkPalette;
//   setTheme: (theme: Theme) => void;
//   setLightPalette: (palette: LightPalette) => void;
//   setDarkPalette: (palette: DarkPalette) => void;
// }

// // ============================================================
// // КОНСТАНТЫ И ХЕЛПЕРЫ (без компонентов — безопасно для Fast Refresh)
// // ============================================================
// export const THEME_STORAGE_KEY = "cool-erp-theme";
// export const LIGHT_PALETTE_STORAGE_KEY = "cool-erp-light-palette";
// export const DARK_PALETTE_STORAGE_KEY = "cool-erp-dark-palette";
// /** Старый ключ тёмной палитры — читаем для миграции существующего выбора. */
// const LEGACY_DARK_PALETTE_KEY = "cool-erp-palette";

// export const LIGHT_PALETTES: ReadonlyArray<{
//   id: LightPalette;
//   label: string;
//   hint: string;
// }> = [
//   { id: "default", label: "Стандартная", hint: "Чистая светлая тема" },
//   { id: "sepia", label: "Сепия", hint: "Спокойная, тёплая, как бумага" },
// ];

// export const DARK_PALETTES: ReadonlyArray<{
//   id: DarkPalette;
//   label: string;
//   hint: string;
// }> = [
//   { id: "default", label: "Стандартная", hint: "Базовая тёмная палитра" },
//   { id: "onedark", label: "One Dark", hint: "Стиль Atom / VS Code" },
//   { id: "nord", label: "Nord", hint: "Холодная арктическая" },
//   { id: "ghdimmed", label: "GitHub Dimmed", hint: "Средний контраст" },
//   { id: "catppuccin", label: "Catppuccin Mocha", hint: "Тёплая пастельная" },
//   { id: "solarized", label: "Solarized", hint: "Низкий контраст, мягкая" },
// ];

// export const getSystemTheme = (): ResolvedTheme =>
//   window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";

// export const getInitialTheme = (): Theme => {
//   const stored = localStorage.getItem(THEME_STORAGE_KEY);
//   if (stored === "light" || stored === "dark" || stored === "system") {
//     return stored;
//   }
//   return "system";
// };

// export const getInitialLightPalette = (): LightPalette => {
//   const stored = localStorage.getItem(LIGHT_PALETTE_STORAGE_KEY);
//   const found = LIGHT_PALETTES.find((p) => p.id === stored);
//   return found ? found.id : "default";
// };

// export const getInitialDarkPalette = (): DarkPalette => {
//   // ✅ Миграция: если нового ключа нет, берём старый выбор тёмной палитры
//   const stored =
//     localStorage.getItem(DARK_PALETTE_STORAGE_KEY) ??
//     localStorage.getItem(LEGACY_DARK_PALETTE_KEY);
//   const found = DARK_PALETTES.find((p) => p.id === stored);
//   return found ? found.id : "default";
// };

// export const ThemeContext = createContext<ThemeContextValue | undefined>(
//   undefined,
// );