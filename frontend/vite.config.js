import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Proxy /api → backend FastAPI (uvicorn) na porta 8010 durante o dev
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8010',
    },
  },
})
