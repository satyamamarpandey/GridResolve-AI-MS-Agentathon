import react from '@vitejs/plugin-react'
// defineConfig from vitest/config, so the `test` block is typed.
import { defineConfig } from 'vitest/config'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  test: {
    // CSS must be processed in tests, otherwise a `?raw` stylesheet import
    // resolves to an empty string and any assertion over its contents passes
    // vacuously. The offline-guarantee test depends on reading the real CSS.
    css: true,
  },
})
