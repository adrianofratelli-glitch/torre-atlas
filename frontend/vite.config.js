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
  preview: {
    port: Number(WEB_PORT),
    strictPort: false,
    proxy: { '/api': `http://localhost:${API_PORT}` },
  },
  build: {
    rollupOptions: {
      output: {
        // Separa as libs pesadas em chunks próprios — melhora cache e elimina
        // o warning de chunk >500 kB do bundle único
        manualChunks(id) {
          if (!id.includes('node_modules')) return
          if (id.includes('@leafygreen-ui') || id.includes('@lg-')) return 'leafygreen'
          if (/node_modules\/(react-markdown|remark-|rehype-|micromark|mdast-|unified|unist-|hast-|vfile|bail|trough|devlop|property-information|space-separated-tokens|comma-separated-tokens|character-entities|decode-named-character-reference|trim-lines|html-url-attributes|estree-util|style-to-(js|object)|inline-style-parser|zwitch|longest-streak|ccount|markdown-table|escape-string-regexp)/.test(id)) return 'markdown'
          return 'vendor'
        },
      },
    },
  },
})
