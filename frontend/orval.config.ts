import { defineConfig } from "orval";

export default defineConfig({
  // 1. Генерация HTTP-клиентов и типов (React Query)
  api: {
    input: './openapi.json',
    // input: {
    //   target: "http://localhost:8000/openapi.json", // ✅ ЖИВОЙ СЕРВЕР
    // },
    output: {
      mode: "tags-split",
      target: "./src/api/generated",
      client: "react-query",
      override: {
        mutator: {
          path: "./src/api/custom-instance.ts",
          name: "customInstance",
        },
        useNativeEnums: true,
        useTypeOverInterfaces: true, // ✅ Помогает со сложными вложенными типами. Добавьте useTypeOverInterfaces: true в блок api (и apiZod, если нужно)
      },
    },
  },

  // 2. Генерация Zod-схем (ОТДЕЛЬНЫЙ блок!)
  apiZod: {
    input: "./openapi.json",
    // input: {
    //   target: "http://localhost:8000/openapi.json", // ✅ ЖИВОЙ СЕРВЕР
    // },
    output: {
      mode: "tags-split",
      client: "zod", // <-- КРИТИЧЕСКИ ВАЖНО: говорим генерировать именно Zod
      target: "./src/api/generated/zod",
      fileExtension: ".schema.ts", // Чтобы файлы не конфликтовали с обычными типами
    },
  },
});
