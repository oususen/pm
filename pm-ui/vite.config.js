import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath, URL } from 'node:url'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const httpsFlag = (env.VITE_HTTPS || '').toLowerCase()
  const useHttps = httpsFlag ? ['true', '1'].includes(httpsFlag) : mode === 'development'
  const httpsKeyPath = env.VITE_HTTPS_KEY || ''
  const httpsCertPath = env.VITE_HTTPS_CERT || ''
  const httpsConfig =
    useHttps && httpsKeyPath && httpsCertPath
      ? {
          key: fs.readFileSync(httpsKeyPath),
          cert: fs.readFileSync(httpsCertPath),
        }
      : useHttps
  const apkHeaderPlugin = {
    name: 'apk-header-plugin',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const requestPath = req.url ? req.url.split('?')[0] : ''
        if (requestPath && requestPath.startsWith('/downloads/') && requestPath.endsWith('.apk')) {
          const filename = path.basename(requestPath)
          res.setHeader('Content-Type', 'application/vnd.android.package-archive')
          res.setHeader('Content-Disposition', `attachment; filename="${filename}"`)
          res.setHeader('X-Content-Type-Options', 'nosniff')
        }
        next()
      })
    },
    configurePreviewServer(server) {
      server.middlewares.use((req, res, next) => {
        const requestPath = req.url ? req.url.split('?')[0] : ''
        if (requestPath && requestPath.startsWith('/downloads/') && requestPath.endsWith('.apk')) {
          const filename = path.basename(requestPath)
          res.setHeader('Content-Type', 'application/vnd.android.package-archive')
          res.setHeader('Content-Disposition', `attachment; filename="${filename}"`)
          res.setHeader('X-Content-Type-Options', 'nosniff')
        }
        next()
      })
    },
  }

  return {
    plugins: [vue(), apkHeaderPlugin],
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
