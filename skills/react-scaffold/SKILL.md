---
name: react-scaffold
description: 搭建与开发 React 19 + Vite + TypeScript + antd 前端工程的通用规范与基础设施。当需要新建前端项目、初始化目录结构、安装基础依赖、接入请求封装/Mock/路由守卫/布局/明暗主题/全局 Sass，或评审前端工程结构时使用。不含任何业务逻辑。
---

# React 前端工程通用 Skill

## Overview

从生产项目提炼的通用前端工程基线：目录设计、基础依赖、公共基础设施（hooks / layout / 路由 / 全局 Sass / 请求封装 / Mock / 主题）。适用于每个新 React 前端项目的初始化与日常开发约束。

## 技术栈基线

React 19 · Vite 6 · TypeScript 5.7（strict 全开）· antd 6 · Redux Toolkit · react-router-dom 7 · axios · Sass · axios-mock-adapter

## 使用方式

按任务查阅对应 reference，按需复制 assets 模板：

| 任务 | 查阅 | 可复制资产 |
| --- | --- | --- |
| 初始化工程目录 | `references/directory.md` | `assets/config/` 全部 |
| 安装依赖 / 配环境变量 | `references/dependencies.md` | `assets/config/package.json`、`.env.*` |
| 入口装配 / 请求封装 / Mock / store / hooks | `references/infrastructure.md` | `assets/core/` |
| 路由体系 / 布局体系 | `references/router-layout.md` | — |
| 全局样式 / 明暗主题 | `references/styling.md` | `assets/styles/` 全部 |
| 单测 / 组件四态测试 | `references/testing.md` | `assets/testing/` 全部 |
| 前端安全项（凭据存储 / XSS / 控制台泄露 / 依赖扫描） | `references/security.md` | `scripts/check_security.sh` |

## 核心纪律（不可违背）

1. **颜色唯一真源**：hex 只允许写在 `styles/theme.css`；业务样式一律 `var(--color-*)` 或 sass 变量，禁止硬编码 hex/rgba。
2. **variables.scss 零输出**：只含变量/mixin/函数，禁止任何 CSS 规则——它被 Vite `additionalData` 注入到每个 .scss 头部，输出规则会重复打包。
3. **请求统一出口**：只走 `api/request.ts` 的 `get/post/put/del`；Result 拆包、错误提示、401 跳转全在拦截器，业务代码拿到的是 `data`。
4. **Mock 无侵入**：用 axios-mock-adapter 替换 adapter，禁止在业务调用处写 mock 分支；mock 走完整拦截器链路；生产构建不含 mock 代码。
5. **Redux 只放跨页共享状态**（主题/系统/登录态/用户）；页面级数据走 `useRequest`，禁止塞进 store。
6. **主题单入口**：切换只调 `useTheme().setTheme`；`<html>` 类名只由 ThemeProvider 写；组件禁止直接改 documentElement。
7. **ID 一律字符串**：后端 Long/雪花 ID 按 string 处理，禁止 Number（精度丢失）；分页统一 `pageNum`（从 1 起）+ `pageSize`。
8. **环境变量**：仅 `VITE_` 前缀暴露给前端，禁止放任何密钥。
9. **前端守卫只管 UI**：路由守卫/权限点只控制渲染，真实鉴权在后端每次请求完成；前端解析 JWT 仅用于展示恢复。
10. **交付门禁**：`npm run typecheck` 0 errors + `npm test` 全绿 + `bash scripts/check_security.sh src` 无 ERROR，均留存真实日志；异步组件必测四态闭环（见 `references/testing.md`），禁止快照测试、禁止真实网络请求。
11. **凭据与个人信息不落浏览器**：Token 只存内存 store（刷新靠 httpOnly Cookie 或重新登录），禁止 `localStorage`/`sessionStorage` 明文存凭据；`dangerouslySetInnerHTML` 必须先过 sanitizer；`console` 不得打印用户数据。要求本身见 `docs/02-protocols/security-baseline.md`（SEC-8 / DP-3 / ID-3），前端落地见 `references/security.md`。
12. **注释即工程产物**：禁止 emoji、图标与 `====` / `----` 分隔横幅；只写功能与非显然约束，与代码同寿命。判据见 `agents/developers/README.md` 第六节。

## 入口装配顺序（main.tsx）

```
装载 mock（VITE_USE_MOCK=true 时动态 import，须先于首次渲染）
→ Redux Provider → ThemeProvider（ConfigProvider + AntdApp）→ App 壳 → Router
```

## assets/core 落位对照

| 资产文件 | 复制到项目位置 |
| --- | --- |
| `useRequest.ts` / `useTheme.ts` | `src/hooks/` |
| `feedback.ts` | `src/api/feedback.ts` |
| `FeedbackBridge.tsx` | `src/components/FeedbackBridge/index.tsx` |
| `themeSlice.ts` / `systemSlice.ts` | `src/store/slices/` |
| `ThemeProvider.tsx` | `src/store/ThemeProvider.tsx` |
| `jwt.ts` | `src/utils/jwt.ts` |

复制后检查：`themeSlice` 的 STORAGE_KEY 前缀按项目改名；`jwt.ts` 的业务 claims 用泛型按契约扩展；`@/` 别名依赖 tsconfig 与 vite.config 同步配置。