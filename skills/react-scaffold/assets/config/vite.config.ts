import { defineConfig } from 'vitest/config';
import { loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/** Vite 构建配置：dev 下 /api 代理到后端避开跨域（后端未就绪时走 src/api/mock），生产由 Nginx 反代同一前缀 */
export default defineConfig(({ mode }) => {
  // 只取 VITE_ 前缀，后端密钥等非 VITE_ 变量不进前端可见范围
  const env = loadEnv(mode, __dirname, 'VITE_');

  /** dev 代理目标，未配置时回退本地 8080；只有 dev server 读它，生产不注入 */
  const backendTarget = env.VITE_BACKEND_ORIGIN || 'http://localhost:8080';

  return {
    plugins: [react()],

    resolve: {
      alias: {
        '@': path.resolve(__dirname, 'src'),
      },
    },

    css: {
      preprocessorOptions: {
        scss: {
          // 全局注入设计令牌，业务样式可直接使用 $color-primary 等变量
          additionalData: `@use "@/styles/variables.scss" as *;`,
        },
      },
    },

    server: {
      host: '0.0.0.0',
      open: false,
      // Windows 原生文件监听（readDirectoryChangesW）长会话会静默失效：改码不触发 HMR、刷新仍是旧模块。
      // 改轮询监听根治，代价仅 dev 下 CPU 略增。
      watch: {
        usePolling: true,
        interval: 300,
      },
      proxy: {
        // 后端无 context-path，接口路径原样透传（前端的 /api 仅作为代理前缀）
        '/api': {
          target: backendTarget,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, ''),
        },
      },
    },

    preview: {
      host: '0.0.0.0',
    },

    // vitest：jsdom 环境；测试文件放 tests/（与 src/ 镜像），也允许就近放 src/
    test: {
      environment: 'jsdom',
      setupFiles: ['src/test/setup.ts'],
      include: ['tests/**/*.{test,spec}.{ts,tsx}', 'src/**/*.{test,spec}.{ts,tsx}'],
      coverage: {
        provider: 'v8',
        reporter: ['text', 'lcov'],
        include: ['src/**'],
        // 默认门槛 70%，项目可在 Tech Spec 中上调
        thresholds: { statements: 70, branches: 70, functions: 70, lines: 70 },
      },
    },

    build: {
      outDir: 'dist',
      sourcemap: mode !== 'production',
      chunkSizeWarningLimit: 1500,
      rollupOptions: {
        output: {
          /** 手动分包：低频大依赖单独成 chunk，配合路由懒加载避免单包过大 */
          manualChunks: {
            'vendor-react': ['react', 'react-dom', 'react-router-dom'],
            'vendor-antd': ['antd', '@ant-design/icons'],
          },
        },
      },
    },
  };
});
