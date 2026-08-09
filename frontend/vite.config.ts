import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'node:path'

// Vite5 + Vue3.4 配置：
// - dev 时 /api 与 /output 代理到 Python FastAPI 后端 (127.0.0.1:8765)
// - 生产构建走 VITE_API_BASE_URL 环境变量
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const backendTarget = env.VITE_BACKEND_TARGET || 'http://127.0.0.1:8765'
  return {
    plugins: [vue()],
    resolve: {
      alias: {
        '@': resolve(__dirname, 'src'),
      },
    },
    css: {
      preprocessorOptions: {
        scss: {
          additionalData: `@use "@/styles/variables.scss" as *;`,
        },
      },
    },
    server: {
      host: '127.0.0.1',
      port: 5173,
      open: false,
      proxy: {
        '/api': {
          target: backendTarget,
          changeOrigin: true,
        },
        '/output': {
          target: backendTarget,
          changeOrigin: true,
        },
      },
    },
    build: {
      outDir: 'dist',
      sourcemap: false,
      chunkSizeWarningLimit: 1500,
    },
  }
})
