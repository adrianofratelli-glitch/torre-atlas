import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Portas configuráveis via env para não colidir com outras POCs.
// Defaults incomuns (8765/5290). run_react.sh injeta portas livres detectadas.
const API_PORT = process.env.API_PORT || '8765'
const WEB_PORT = process.env.WEB_PORT || '5290'

export default defineConfig({
  plugins: [react()],
  server: {
    port: Number(WEB_PORT),
    strictPort: false,            // se ocupada, o Vite tenta a próxima livre
    proxy: {
      '/api': `http://localhost:${API_PORT}`,
    },
  },
})
