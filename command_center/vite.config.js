import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

const normalizeTarget = (value) => String(value || '').trim().replace(/\/+$/, '')

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const backendTarget = normalizeTarget(
    env.VITE_DEV_PROXY_TARGET || env.VITE_API_BASE_URL || 'http://localhost:8000'
  )

  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: backendTarget,
          changeOrigin: true
        },
        '/ws': {
          target: backendTarget,
          changeOrigin: true,
          ws: true
        },
        '/scenario-assets': {
          target: backendTarget,
          changeOrigin: true
        }
      }
    },
    build: {
      outDir: 'dist',
      sourcemap: true
    }
  }
})
