import { defineConfig } from "orval";

export default defineConfig({
  // 1. HTTP-клиенты и типы (React Query)
  api: {
    input: "./openapi.json",
    output: {
      mode: "tags-split",
      target: "./src/api/generated",
      client: "react-query",
      httpClient: "axios", // ✅ Пункт 2 миграции: согласуем с axios-мутатором
      override: {
        mutator: {
          path: "./src/api/custom-instance.ts",
          name: "customInstance",
        },
        enumGenerationType: "enum", // ✅ Пункт 6: замена удалённого useNativeEnums (внутри override)
        useTypeOverInterfaces: true,
      },
    },
  },

  // 2. Zod-схемы (отдельный блок)
  apiZod: {
    input: "./openapi.json",
    output: {
      mode: "tags-split",
      client: "zod",
      target: "./src/api/generated/zod",
      fileExtension: ".schema.ts",
    },
  },
});