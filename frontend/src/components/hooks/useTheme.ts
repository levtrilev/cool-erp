import { useContext } from "react";
import {
  ThemeContext,
  type ThemeContextValue,
} from "@/components/theme/theme-context";

/**
 * Хук доступа к теме.
 * Вынесен в отдельный файл: Fast Refresh требует, чтобы файлы
 * с компонентами экспортировали ТОЛЬКО компоненты.
 */
export const useTheme = (): ThemeContextValue => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme должен использоваться внутри ThemeProvider");
  }
  return context;
};