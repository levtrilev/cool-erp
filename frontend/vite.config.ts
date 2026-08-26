import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  resolve: {
    // Нативная поддержка алиасов из tsconfig.json (вместо плагина vite-tsconfig-paths)
    tsconfigPaths: true,
  },
})