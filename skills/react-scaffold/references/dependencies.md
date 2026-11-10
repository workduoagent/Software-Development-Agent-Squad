# 基础依赖与环境变量

完整可复制的 `package.json` 见 `assets/config/package.json`（name 按项目改）。

## dependencies（运行期）

| 包 | 版本基线 | 用途 |
| --- | --- | --- |
| react / react-dom | ^19.0.0 | 框架 |
| react-router-dom | ^7.1.1 | 数据路由（createBrowserRouter / lazy） |
| @reduxjs/toolkit / react-redux | ^2.5.0 / ^9.2.0 | 跨页共享状态 |
| axios | ^1.7.9 | 请求封装（拦截器拆包） |
| antd / @ant-design/icons | ^6.0.0 | 组件库与组件图标 |
| lucide-react | ^0.460.0 | 布局/导航线性图标 |

## devDependencies（构建期）

| 包 | 版本基线 | 用途 |
| --- | --- | --- |
| vite / @vitejs/plugin-react | ^6.0.7 / ^4.3.4 | 构建与 React 刷新 |
| typescript | ^5.7.3 | 类型检查（tsc -b，noEmit） |
| sass | ^1.99.0 | scss 编译（现代 API，@use） |
| axios-mock-adapter | ^2.1.0 | 开发期 mock（替换 adapter）+ 单测拦截 |
| vitest / @vitest/coverage-v8 / jsdom | ^3.0.0 / ^3.0.0 / ^26.0.0 | 单测运行器、覆盖率、浏览器环境模拟 |
| @testing-library/react / user-event / jest-dom | ^16.2.0 / ^14.6.0 / ^6.6.3 | 组件测试（用户视角渲染、交互、断言） |
| @types/react / @types/react-dom / @types/node | ^19 / ^19 / ^22 | 类型 |

**不纳入基线**：xlsx 等业务专属包（按需单独引入）。测试基线与必测清单见 `references/testing.md`。

## scripts

```json
"dev": "vite",
"build": "tsc -b && vite build",
"preview": "vite preview",
"typecheck": "tsc -b --pretty",
"test": "vitest run",
"test:watch": "vitest",
"coverage": "vitest run --coverage"
```

`build` 必须先过 `tsc -b`：类型错误即构建失败，不允许带错出包。`typecheck` 与 `test` 是交付门禁（见 `references/testing.md`）。

## 环境变量（.env.*）

| 变量 | 说明 |
| --- | --- |
| `VITE_APP_TITLE` | 浏览器标题后缀、缺省品牌名 |
| `VITE_APP_BRAND` | 顶栏/侧栏品牌名，缺省回退 TITLE |
| `VITE_API_BASE_URL` | 接口统一前缀，默认 `/api`（配合 dev 代理 / Nginx） |
| `VITE_BACKEND_ORIGIN` | 后端真实地址，仅 dev 代理用 |
| `VITE_USE_MOCK` | `true` 启用本地 mock；后端就绪改 `false`，业务零改动；生产必须 `false` |
| `VITE_ROUTER_MODE` | `hash` \| `history`；Nginx 子路径部署用 hash |

纪律：只有 `VITE_` 前缀会打进产物，**禁止放密钥**；`.env.*` 可提交 git；新增变量必须同步在 `src/vite-env.d.ts` 声明类型（模板见 `assets/config/vite-env.d.ts`）。
密钥与凭据的存放边界、`VITE_USE_MOCK` 交付前必须收敛的要求见 `references/security.md`（要求本体是 `docs/02-protocols/security-baseline.md`），由 `scripts/check_security.sh` 的 F004/F007 机检。

## 构建配置要点（assets/config/vite.config.ts）

- `@` → `src` 别名；scss `additionalData` 全局注入 variables.scss。
- dev 代理 `/api` → `VITE_BACKEND_ORIGIN`，rewrite 剥离前缀（后端无 context-path 时）。
- **Windows 必须 `server.watch.usePolling: true`**：原生文件监听长会话中静默失效，表现为改了代码 HMR 不触发。
- `test` 块（vitest）：jsdom 环境、`src/test/setup.ts` 全局初始化、覆盖率门槛默认 70%；`defineConfig` 从 `vitest/config` 导入以获取 test 字段类型。
- 手动分包：`vendor-react`（react 全家桶）、`vendor-antd`（antd + icons），配合路由懒加载。