# Переключение светлой/тёмной темы (shadcn/ui + Tailwind)

В нашем стеке (Tailwind + shadcn/ui) тема переключается классом `dark` на `<html>`, а все цвета компонентов берутся из CSS-переменных. Реализация состоит из 6 шагов.

## Шаг 1. `tailwind.config.js` — включите class-стратегию

```js
/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"], // ✅ Ключевая строка
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  // ... остальное без изменений
};
```

## Шаг 2. `src/index.css` — проверьте блок `.dark`

Если при инициализации shadcn/ui блок уже есть — ничего не делайте. Если нет, добавьте после `:root { ... }`:

```css
.dark {
  --background: 240 10% 3.9%;
  --foreground: 0 0% 98%;
  --card: 240 10% 3.9%;
  --card-foreground: 0 0% 98%;
  --popover: 240 10% 3.9%;
  --popover-foreground: 0 0% 98%;
  --primary: 0 0% 98%;
  --primary-foreground: 240 5.9% 10%;
  --secondary: 240 3.7% 15.9%;
  --secondary-foreground: 0 0% 98%;
  --muted: 240 3.7% 15.9%;
  --muted-foreground: 240 5% 64.9%;
  --accent: 240 3.7% 15.9%;
  --accent-foreground: 0 0% 98%;
  --destructive: 0 62.8% 30.6%;
  --destructive-foreground: 0 0% 98%;
  --border: 240 3.7% 15.9%;
  --input: 240 3.7% 15.9%;
  --ring: 240 4.9% 83.9%;
}
```

## Шаг 3. Создайте `src/components/theme/ThemeProvider.tsx`

```tsx
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export type Theme = "light" | "dark" | "system";
type ResolvedTheme = "light" | "dark";

interface ThemeContextValue {
  theme: Theme;
  resolvedTheme: ResolvedTheme;
  setTheme: (theme: Theme) => void;
}

const STORAGE_KEY = "cool-erp-theme";

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

const getSystemTheme = (): ResolvedTheme =>
  window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";

const getInitialTheme = (): Theme => {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === "light" || stored === "dark" || stored === "system") {
    return stored;
  }
  return "system";
};

export const ThemeProvider = ({ children }: { children: ReactNode }) => {
  const [theme, setThemeState] = useState<Theme>(getInitialTheme);
  const [resolvedTheme, setResolvedTheme] = useState<ResolvedTheme>(() => {
    const initial = getInitialTheme();
    return initial === "system" ? getSystemTheme() : initial;
  });

  // ✅ Применение класса + подписка на смену системной темы
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

  const setTheme = useCallback((next: Theme) => {
    localStorage.setItem(STORAGE_KEY, next);
    setThemeState(next);
  }, []);

  const value = useMemo<ThemeContextValue>(
    () => ({ theme, resolvedTheme, setTheme }),
    [theme, resolvedTheme, setTheme],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
};

// ✅ Строгая типизация: ошибка вместо undefined вне провайдера
export const useTheme = (): ThemeContextValue => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme должен использоваться внутри ThemeProvider");
  }
  return context;
};
```

## Шаг 4. Создайте переключатель `src/components/theme/ThemeToggle.tsx`

```tsx
import { Check, Moon, Monitor, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useTheme, type Theme } from "@/components/theme/ThemeProvider";

const THEME_OPTIONS: Array<{ value: Theme; label: string; icon: typeof Sun }> = [
  { value: "light", label: "Светлая", icon: Sun },
  { value: "dark", label: "Тёмная", icon: Moon },
  { value: "system", label: "Как в системе", icon: Monitor },
];

export const ThemeToggle = () => {
  const { theme, resolvedTheme, setTheme } = useTheme();

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" title="Тема оформления">
          {resolvedTheme === "dark" ? (
            <Moon className="h-4 w-4" />
          ) : (
            <Sun className="h-4 w-4" />
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {THEME_OPTIONS.map((option) => {
          const Icon = option.icon;
          return (
            <DropdownMenuItem
              key={option.value}
              onClick={() => setTheme(option.value)}
            >
              <Icon className="mr-2 h-4 w-4" />
              {option.label}
              {theme === option.value && (
                <Check className="ml-auto h-4 w-4 text-primary" />
              )}
            </DropdownMenuItem>
          );
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  );
};
```

## Шаг 5. Оберните приложение в `App.tsx`

```tsx
import { ThemeProvider } from "@/components/theme/ThemeProvider";

function App() {
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <Routes>
            {/* ... маршруты без изменений ... */}
          </Routes>
        </BrowserRouter>
        <Toaster />
      </QueryClientProvider>
    </ThemeProvider>
  );
}
```

## Шаг 6. Разместите переключатель в шапке `AppLayout.tsx`

Найдите правый контейнер шапки (рядом с меню пользователя) и добавьте:

```tsx
import { ThemeToggle } from "@/components/theme/ThemeToggle";

// Внутри header, рядом с существующими кнопками:
<div className="flex items-center gap-2">
  <ThemeToggle />
  {/* ... существующий UserOnLayout и пр. ... */}
</div>
```

При желании добавьте `<ThemeToggle />` также на `LoginPage` и `PublicHomePage` — провайдер общий, переключатель работает везде.

## Шаг 7 (рекомендуется). `index.html` — защита от «мигания» темы

Без этого при перезагрузке в тёмной теме будет видна вспышка светлого фона. Добавьте в `<head>` **до** подключения скриптов:

```html
<script>
  (function () {
    try {
      var stored = localStorage.getItem("cool-erp-theme");
      var dark =
        stored === "dark" ||
        (!stored && window.matchMedia("(prefers-color-scheme: dark)").matches);
      if (dark) document.documentElement.classList.add("dark");
    } catch (e) {}
  })();
</script>
```

---

## Нюансы для вашего кода

1. **Жёстко заданные цвета.** В таблицах и ссылках у вас встречаются прямые классы (`text-blue-600`, `bg-yellow-100`, `text-green-600`). В тёмной теме они читаемы, но для полировки добавьте dark-варианты точечно:
   ```tsx
   className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300"
   ```
   Семантические классы shadcn (`bg-background`, `text-muted-foreground`, `border`) переключаются автоматически.
2. **`resolvedTheme` vs `theme`.** Для иконки используйте `resolvedTheme` (фактическое значение), для галочки в меню — `theme` (выбор пользователя). Это уже учтено в `ThemeToggle`.
3. **Правило №46 соблюдено:** состояние темы — одно, в контексте; применение класса — в одном `useEffect`; никаких каскадных setState.

## Чек-лист

- [ ] `tailwind.config.js`: `darkMode: ["class"]`
- [ ] `index.css`: есть блок `.dark` с переменными
- [ ] Создан `ThemeProvider.tsx`
- [ ] Создан `ThemeToggle.tsx`
- [ ] `App.tsx`: обёртка `<ThemeProvider>`
- [ ] `AppLayout.tsx`: `<ThemeToggle />` в шапке
- [ ] `index.html`: анти-мигание скрипт
- [ ] Проверка: переключение на тёмную → перезагрузка страницы → тема сохраняется
- [ ] Проверка: режим «Как в системе» реагирует на смену темы ОС без перезагрузки

После применения все компоненты shadcn (диалоги, таблицы, тосты, меню) перейдут на тёмную палитру автоматически, так как используют CSS-переменные.

Чек-лист(несколько палитр-переключение)
theme-context.ts: добавлены ThemePalette, THEME_PALETTES, PALETTE_STORAGE_KEY, getInitialPalette; контекст расширен (palette, setPalette)
ThemeProvider.tsx: состояние палитры + эффект применения класса только при resolvedTheme === "dark"
ThemeToggle.tsx: меню с режимами и списком палитр
index.html: анти-мигание с whitelist палитр
index.css: блоки .dark.palette-* присутствуют и идут после .dark
hooks/useTheme.ts не изменялся (контекст уже возвращает всё нужное)
Проверка: переключение палитр меняет тему мгновенно; после F5 выбор сохраняется; в светлом режиме палитра не применяется
Дополнительно: если захотите добавить новую палитру — достаточно (1) добавить блок .dark.palette-<id> в CSS, (2) добавить id в тип ThemePalette и в массив THEME_PALETTES, (3) добавить id в whitelist скрипта в index.html. Больше ничего менять не нужно.