// frontend/src/lib/ui-preferences/browserAppearance.ts
import {
  NavigationPreferenceSchemaLayout,
  ThemePreferenceSchemaMode,
} from "@/api/generated/coolERP.schemas";
import {
  DARK_PALETTES,
  LIGHT_PALETTES,
  getInitialDarkPalette,
  getInitialLightPalette,
  getInitialTheme,
} from "@/components/theme/theme-context";
import {
  normalizeDarkPalette,
  normalizeLightPalette,
  toApiThemeMode,
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

/**
 * Все классы палитр проекта — из единственного источника theme-context.ts.
 * Нужны, чтобы снимать чужие/устаревшие классы перед установкой активного.
 */
const KNOWN_PALETTE_CLASSES: ReadonlySet<string> = new Set<string>([
  ...LIGHT_PALETTES.map((p) => PALETTE_CLASS_PREFIX + p.id),
  ...DARK_PALETTES.map((p) => PALETTE_CLASS_PREFIX + p.id),
]);

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
 * Поэтому applyTheme снимает все известные классы палитр и ставит активный,
 * иначе чужой класс (например, palette-sepia из старого скрипта) перекрывает
 * переменные тёмной темы и цвета не меняются.
 *
 * Data-атрибуты дублируют состояние машиночитаемо (отладка, будущие селекторы),
 * но на цвета они не влияют.
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

  // ✅ Снимаем устаревшие классы палитр, ставим активный (контракт index.css).
  KNOWN_PALETTE_CLASSES.forEach((cls) => root.classList.remove(cls));
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
 * Приоритет: cookie (последнее применённое) → прежний выбор из localStorage.
 * Второй источник сохраняет выбор пользователей, сделанный до перехода
 * на серверные настройки; запись на сервер выполняется при первом действии.
 */
export const readInitialAppearance = (): UiThemePreference => {
  const storedTheme: string | null = readCookie(THEME_COOKIE);
  const storedLight: string | null = readCookie(LIGHT_PALETTE_COOKIE);
  const storedDark: string | null = readCookie(DARK_PALETTE_COOKIE);

  if (storedTheme === "light" || storedTheme === "dark") {
    return {
      mode: toApiThemeMode(storedTheme),
      lightPalette: normalizeLightPalette(
        storedLight ?? getInitialLightPalette(),
      ),
      darkPalette: normalizeDarkPalette(storedDark ?? getInitialDarkPalette()),
    };
  }

  return {
    mode: toApiThemeMode(getInitialTheme()),
    lightPalette: getInitialLightPalette(),
    darkPalette: getInitialDarkPalette(),
  };
};

/** Последняя известная раскладка — для первого рендера до ответа сервера. */
export const readNavigationLayoutCookie = (): NavigationLayout | null => {
  const raw: string | null = readCookie(NAV_LAYOUT_COOKIE);
  if (raw === null) return null;
  const allowed: readonly string[] = Object.values(
    NavigationPreferenceSchemaLayout,
  );
  return allowed.includes(raw) ? (raw as NavigationLayout) : null;
};