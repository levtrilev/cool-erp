export default {
  plugins: {
    'postcss-nesting': {}, // <-- ДОЛЖЕН БЫТЬ ПЕРЕД tailwindcss
    tailwindcss: {},
    autoprefixer: {},
  },
}
