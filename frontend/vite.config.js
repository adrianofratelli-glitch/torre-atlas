import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { nodePolyfills } from 'vite-plugin-node-polyfills'

// Portas configuráveis via env (não colidem com outras POCs). Defaults 8765/5290.
const API_PORT = process.env.API_PORT || '8765'
const WEB_PORT = process.env.WEB_PORT || '5290'

export default defineConfig({
  plugins: [
    react(),
    // Polyfills de Buffer/global/process — algumas deps transitivas do LeafyGreen
    // (readable-stream/through) usam globais do Node que não existem no browser.
    nodePolyfills({ globals: { Buffer: true, global: true, process: true } }),
  ],
  server: {
    port: Number(WEB_PORT),
    strictPort: false,
    proxy: { '/api': `http://localhost:${API_PORT}` },
  },
})
