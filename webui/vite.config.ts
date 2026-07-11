import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Relative asset URLs (base: './') so the built console works behind an
// arbitrary reverse-proxy prefix (UVICORN_ROOT_PATH) when served from /web/.
export default defineConfig({
  base: './',
  plugins: [react()],
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
})
