import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'node:path'

// 端口必须与 src-tauri/tauri.conf.json 的 build.devUrl 逐字一致，
// strictPort 让端口被占用时直接失败而不是静默漂移（漂移的症状是桌面窗口白屏）。
export default defineConfig({
  plugins: [react()],
  resolve: { alias: { '@': path.resolve(__dirname, 'src') } },
  server: {
    port: 1420,
    strictPort: true,
  },
})
