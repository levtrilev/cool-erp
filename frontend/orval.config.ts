import { defineConfig } from 'orval';

export default defineConfig({
  // 1. Генерация HTTP-клиентов и типов (React Query)
  api: {
    input: './openapi.json',
    output: {
      mode: 'tags-split',
      target: './src/api/generated',
      client: 'react-query',
      override: {
        mutator: {
          path: './src/api/custom-instance.ts',
          name: 'customInstance',
        },
        useNativeEnums: true,
      },
    },
  },
  
  // 2. Генерация Zod-схем (ОТДЕЛЬНЫЙ блок!)
  apiZod: {
    input: './openapi.json',
    output: {
      mode: 'tags-split',
      client: 'zod', // <-- КРИТИЧЕСКИ ВАЖНО: говорим генерировать именно Zod
      target: './src/api/generated/zod',
      fileExtension: '.schema.ts', // Чтобы файлы не конфликтовали с обычными типами
    },
  },
});