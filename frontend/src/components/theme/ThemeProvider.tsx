import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  ThemeContext,
  LIGHT_PALETTES,
  DARK_PALETTES,
  THEME_STORAGE_KEY,
  LIGHT_PALETTE_STORAGE_KEY,
  DARK_PALETTE_STORAGE_KEY,
  getInitialTheme,
  getInitialLightPalette,
  getInitialDarkPalette,
  getSystemTheme,
  type ResolvedTheme,
  type Theme,
  type LightPalette,
  type DarkPalette,
  type ThemeContextValue,
} from "./theme-context";

interface ThemeProviderProps {
  children: ReactNode;
}

/**
 * ✅ Файл экспортирует ТОЛЬКО компонент (требование Fast Refresh).
 * Управляет режимом и раздельными палитрами для светлой/тёмной темы.
 */
export const ThemeProvider = ({ children }: ThemeProviderProps) => {
  const [theme, setThemeState] = useState<Theme>(getInitialTheme);
  const [lightPalette, setLightPaletteState] =
    useState<LightPalette>(getInitialLightPalette);
  const [darkPalette, setDarkPaletteState] =
    useState<DarkPalette>(getInitialDarkPalette);
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

  // ✅ Палитра применяется только при совпадении её типа с активным режимом:
  // светлая палитра — в светлой теме, тёмная — в тёмной.
  useEffect(() => {
    const root = document.documentElement;
    for (const p of [...LIGHT_PALETTES, ...DARK_PALETTES]) {
      if (p.id !== "default") {
        root.classList.remove(`palette-${p.id}`);
      }
    }
    const active = resolvedTheme === "light" ? lightPalette : darkPalette;
    if (active !== "default") {
      root.classList.add(`palette-${active}`);
    }
  }, [lightPalette, darkPalette, resolvedTheme]);

  const setTheme = useCallback((next: Theme) => {
    localStorage.setItem(THEME_STORAGE_KEY, next);
    setThemeState(next);
  }, []);

  const setLightPalette = useCallback((next: LightPalette) => {
    localStorage.setItem(LIGHT_PALETTE_STORAGE_KEY, next);
    setLightPaletteState(next);
  }, []);

  const setDarkPalette = useCallback((next: DarkPalette) => {
    localStorage.setItem(DARK_PALETTE_STORAGE_KEY, next);
    setDarkPaletteState(next);
  }, []);

  const value = useMemo<ThemeContextValue>(
    () => ({
      theme,
      resolvedTheme,
      lightPalette,
      darkPalette,
      setTheme,
      setLightPalette,
      setDarkPalette,
    }),
    [
      theme,
      resolvedTheme,
      lightPalette,
      darkPalette,
      setTheme,
      setLightPalette,
      setDarkPalette,
    ],
  );

  return (
    <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
  );
};