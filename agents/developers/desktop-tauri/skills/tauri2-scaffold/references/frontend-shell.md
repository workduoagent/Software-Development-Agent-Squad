# 前端基座（桌面形态）

通用 React 分层规范见 `react-scaffold/`，本文件只写桌面形态必须不同的部分与可直接复制的模板。

## 1. 配置要点

### `tsconfig.json`

必须开 `strict` + `noUnusedLocals` + `noUnusedParameters`（`typecheck` 0 错 0 警是交付判据），`paths` 别名 `@/*` → `src/*` 与 `vite.config.ts` 的 alias 同步。完整模板：`assets/config/tsconfig.json`。

### `vite.config.ts`

```ts
export default defineConfig({
  plugins: [react()],
  resolve: { alias: { '@': path.resolve(__dirname, 'src') } },
  server: {
    port: 1420,       // 固定端口，与 tauri.conf.json 的 devUrl 对齐
    strictPort: true  // 端口被占用直接报错，不静默漂移
  }
})
```

`vite.config.ts` 由维护者管理，业务代码不要改。完整模板：`assets/config/vite.config.ts`。

### `tauri.conf.json`

`build.devUrl` 必须与 vite 端口逐字一致（`http://localhost:1420`），`frontendDist` 指向 `../dist` 且**不要手动 build**。完整模板：`assets/config/tauri.conf.json`。

### `package.json` scripts

```json
{
  "dev": "vite",
  "build": "tsc && vite build",
  "preview": "vite preview",
  "typecheck": "tsc --noEmit",
  "tauri": "tauri dev",
  "tauri:build": "tauri build"
}
```

## 2. 入口与路由

路由**必须** `createHashRouter`。原因：Tauri 走 `tauri://` 协议，没有 SPA fallback，`createBrowserRouter` 一刷新就 404。

```tsx
// src/main.tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { RouterProvider } from 'react-router-dom'
import { App as AntdApp, ConfigProvider, theme } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import { router } from './core/router'
import './styles/tokens.scss'
import './styles/global.scss'

const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ConfigProvider
      locale={zhCN}
      theme={{ algorithm: isDark ? theme.darkAlgorithm : theme.defaultAlgorithm }}
    >
      <AntdApp>
        <RouterProvider router={router} />
      </AntdApp>
    </ConfigProvider>
  </React.StrictMode>
)
```

```tsx
// src/core/router/index.tsx
import { createHashRouter } from 'react-router-dom'
import HomePage from '@/pages/home'

export const router = createHashRouter([
  { path: '/', element: <HomePage /> },
])
```

路径常量集中在 `core/router/paths.ts`，路由表与菜单都从这里取，禁止散落字面量。

## 3. 全局消息

```tsx
// src/components/ui/notify.tsx
import { App } from 'antd'

/** 全局消息 hook——必须走此封装，禁静态 import { message } from 'antd' */
export function useNotify() {
  const { message, notification, modal } = App.useApp()
  return { message, notification, modal }
}
```

静态 `message` 脱离 `<App>` 上下文，会导致主题不跟随、位置被顶栏遮挡。

与 `react-scaffold` 的 `FeedbackBridge` 关系：那座桥是为 axios 拦截器（在 React 树外）准备的，桌面工程无 axios，**不需要 FeedbackBridge**，组件内一律 `useNotify()`。

## 4. 设计令牌

明暗切换走 `html.light` / `html.dark` 类 + CSS 变量，组件样式一律 `var(--color-*)`，禁止硬编码色值。模板：`assets/styles/tokens.scss`。

`IPC` 与类型对齐见 `ipc-and-types.md`；建表与 mapper 红线同文件 §4。

## 5. 桌面前端红线（命中即打回）

1. 裸用 antd 底层组件、混用无关图标库。
2. 在 `components/` 写页面业务；页面私有组件放进公共目录。
3. 组件直连 DB、散落 SQL、裸 `invoke`。
4. 内联样式魔法数与硬编码颜色。
5. `typecheck` 未过就交付。
6. 静态 `import { message } from 'antd'`——必须走 `useNotify()`。
7. 用 `createBrowserRouter`。
8. `@import` 引入 scss（deprecation 警告），改 `@use`。
9. 表单输入框不设 `autoComplete="off"`。
10. 给根容器设 `max-width` + `margin: 0 auto` 居中限制——桌面窗口宽度由用户拖，一级页面根容器 `width: 100%`。
11. 留 `console.log`，统一走 `utils/logger.ts`。
12. 文案「中文（English）」混排；纯中文或纯英文缩写（ID/URL）。
13. hover 效果带位移/缩放。

## 6. 布局约定

- 卡片网格统一 `repeat(auto-fill, minmax(260px, 1fr))`。
- 侧栏固定列宽（如 220px），主区 `1fr` 占满剩余。
- 重型库必须 `import()` 懒加载 + `types/shims.d.ts` 补类型。

## 7. 提交前自检（桌面前端专属项，通用项见 react-scaffold）

- [ ] 路由用 `createHashRouter`，`paths.ts` 为唯一路径来源
- [ ] `vite.config.ts` 端口 1420 + `strictPort`，与 `devUrl` 一致
- [ ] 未手动跑 `npm run build`（`dist` 由 tauri 自己产）
- [ ] 所有后端调用经 `core/ipc`，无裸 `invoke`
- [ ] Rust struct 与 `types/core.d.ts` 逐字段核对一致
- [ ] 消息提示全部走 `useNotify()`
- [ ] `npm run typecheck` EXIT 0
