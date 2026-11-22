import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// The browser only ever talks to OUR backend (/api). The Infloww key never reaches the frontend.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { proxy: { '/api': 'http://127.0.0.1:8000' } },
  build: {
    chunkSizeWarningLimit: 900,
    // VITE_STATIC builds a single-file snapshot (scripts/build-static.mjs), so no lazy chunks.
    rollupOptions: (globalThis as any).process?.env?.VITE_STATIC ? { output: { inlineDynamicImports: true } } : {},
  },
})
