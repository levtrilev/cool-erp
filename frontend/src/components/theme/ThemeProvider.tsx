import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  ThemeContext,
  THEME_PALETTES,
  THEME_STORAGE_KEY,
  PALETTE_STORAGE_KEY,
  getInitialTheme,
  getInitialPalette,
  getSystemTheme,
  type ResolvedTheme,
  type Theme,
  type ThemePalette,
  type ThemeContextValue,
} from "./theme-context";

interface ThemeProviderProps {
  children: ReactNode;
}

/**
 * ✅ Файл экспортирует ТОЛЬКО компонент (требование Fast Refresh).
 * Управляет режимом (light/dark/system) и палитрой тёмной темы.
 */
export const ThemeProvider = ({ children }: ThemeProviderProps) => {
  const [theme, setThemeState] = useState<Theme>(getInitialTheme);
  const [palette, setPaletteState] = useState<ThemePalette>(getInitialPalette);
  const [resolvedTheme, setResolvedTheme] = useState<ResolvedTheme>(() => {
    const initial = getInitialTheme();
    return initial === "system" ? getSystemTheme() : initial;
  });

  // Применение режима + подписка на смену системной темы
  useEffect(() => {
    const root = document.documentElement;
    const apply = (value: ResolvedTheme) => {
      root.classList.toggle("dark", value === "dark");
      setResolvedTheme(value);
    };

    if (theme === "system") {
      const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
      apply(mediaQuery.matches ? "dark" : "light");
      const handler = (event: MediaQueryListEvent) =>
        apply(event.matches ? "dark" : "light");
      mediaQuery.addEventListener("change", handler);
      return () => mediaQuery.removeEventListener("change", handler);
    }

    apply(theme);
    return undefined;
  }, [theme]);

  // ✅ Класс палитры активен ТОЛЬКО в тёмной теме.
  // Сначала снимаем все классы палитр, затем ставим нужный.
  useEffect(() => {
    const root = document.documentElement;
    for (const p of THEME_PALETTES) {
      root.classList.remove(`palette-${p.id}`);
    }
    if (resolvedTheme === "dark" && palette !== "default") {
      root.classList.add(`palette-${palette}`);
    }
  }, [palette, resolvedTheme]);

  const setTheme = useCallback((next: Theme) => {
    localStorage.setItem(THEME_STORAGE_KEY, next);
    setThemeState(next);
  }, []);

  const setPalette = useCallback((next: ThemePalette) => {
    localStorage.setItem(PALETTE_STORAGE_KEY, next);
    setPaletteState(next);
  }, []);

  const value = useMemo<ThemeContextValue>(
    () => ({ theme, resolvedTheme, palette, setTheme, setPalette }),
    [theme, resolvedTheme, palette, setTheme, setPalette],
  );

  return (
    <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
  );
};