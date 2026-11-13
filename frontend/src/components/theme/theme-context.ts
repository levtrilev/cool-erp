// frontend/src/components/theme/theme-context.ts
/**
 * Каталог палитр темы — единственный источник истины для идентификаторов,
 * подписей и пояснений.
 * ThemeContext, ThemeProvider, useTheme и localStorage-хелперы старой
 * локальной схемы удалены: настройки темы живут в user_ui_preferences (БД),
 * кэш первого кадра — в cookie (см. browserAppearance.ts и index.html).
 */

/** Палитры светлой темы. "default" — базовый :root без переопределений. */
export type LightPalette = "default" | "sepia";

/** Палитры тёмной темы. "default" — базовый .dark без переопределений. */
export type DarkPalette =
  | "default"
  | "onedark"
  | "nord"
  | "ghdimmed"
  | "catppuccin"
  | "solarized";

export const LIGHT_PALETTES: ReadonlyArray<{
  id: LightPalette;
  label: string;
  hint: string;
}> = [
  { id: "default", label: "Стандартная", hint: "Чистая светлая тема" },
  { id: "sepia", label: "Сепия", hint: "Спокойная, тёплая, как бумага" },
];

export const DARK_PALETTES: ReadonlyArray<{
  id: DarkPalette;
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