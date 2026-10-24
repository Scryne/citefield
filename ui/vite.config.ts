import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The built UI ships inside the Python package and is served by `citefield serve`.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: { outDir: '../src/citefield/web', emptyOutDir: true },
  server: { proxy: { '/api': 'http://127.0.0.1:8484' } },
})
