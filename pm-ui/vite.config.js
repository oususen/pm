import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import fs from 'node:fs'
import { fileURLToPath, URL } from 'node:url'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const useHttps = ['true', '1'].includes((env.VITE_HTTPS || '').toLowerCase())
  const httpsKeyPath = env.VITE_HTTPS_KEY || ''
  const httpsCertPath = env.VITE_HTTPS_CERT || ''
  const httpsConfig =
    useHttps && httpsKeyPath && httpsCertPath
      ? {
          key: fs.readFileSync(httpsKeyPath),
          cert: fs.readFileSync(httpsCertPath),
        }
      : useHttps

  return {
    plugins: [vue()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    server: {
      port: 8501,
      host: true,
      https: httpsConfig,
      proxy: {
        '/api': {
          target: 'http://127.0.0.1:8081',
          changeOrigin: true,
        },
        '/media': {
          target: 'http://127.0.0.1:8081',
          changeOrigin: true,
        },
      },
    },
    preview: {
      port: 8501,
      host: true,
      https: httpsConfig,
    },
  }
})
