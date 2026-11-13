import js from "@eslint/js";
import globals from "globals";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import tseslint from "typescript-eslint";
import { defineConfig, globalIgnores } from "eslint/config";

export default defineConfig([
  globalIgnores(["dist", "src/api/generated"]),
  {
    files: ["**/*.{ts,tsx}"],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      globals: globals.browser,
    },
    rules: {
      // ✅ Разрешаем экспорт констант вместе с компонентами.
      // Это стандартный паттерн shadcn/ui: файл экспортирует компонент +
      // константу вариантов стилей (badgeVariants, buttonVariants и т.п.),
      // созданную через cva. Без этой опции ESLint выдаёт ошибку
      // react-refresh/only-export-components на каждом shadcn-компоненте.
      "react-refresh/only-export-components": [
        "warn",
        { allowConstantExport: true },
      ],
    },
  },
]);
