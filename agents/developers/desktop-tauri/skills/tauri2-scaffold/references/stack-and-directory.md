# 技术栈基线与目录骨架

## 1. 架构总览

```
┌──────────────── 桌面应用（Tauri 2）────────────────┐
│  系统 WebView（Windows WebView2 / macOS WKWebView） │
│  ┌──────────── React 19 前端 ────────────┐          │
│  │ pages/      页面（业务自建）          │          │
│  │ components/ UI 封装 + 业务组件         │          │
│  │ core/       路由 / 数据 / IPC / 配置  │          │
│  │ store/      全局状态                  │          │
│  │ types/      类型定义                  │          │
│  └──────────────┬───────────────────────┘          │
└─────────────────┼──────────────────────────────────┘
      invoke ↓            ↑ event        ↓ invoke
┌──────────────── Rust 后端 ────────────────────────┐
│  lib.rs        命令注册入口 + 启动钩子              │
│  <modules>/    业务模块（自建）                     │
│  logging.rs    日志初始化                           │
│  fs_helper.rs  文件读写                             │
│  net.rs        网络请求                             │
│  db.rs         数据访问（引擎侧）                    │
└───────────────┬───────────────────────────────────┘
                ↓
        SQLite（本地单文件数据库）
```

## 2. 分层铁律

| 层 | 职责 | 禁止 |
| --- | --- | --- |
| 页面 `pages/` | 业务编排与展示 | 禁止直接写 SQL、禁止裸 `invoke` |
| 数据 `core/mapper/` | 全部 SQL 与数据读写 | 禁止写 UI 逻辑 |
| 后端 `src-tauri/src/` | 计算、原生能力、长期任务 | 禁止做前端页面逻辑 |
| 通信 | 仅经 Tauri command（请求-响应）/ event（单向推送） | 禁止绕过 IPC 直连 |

代码归属只有这一张表，评审按表判定，不接受"这个特殊"：

| 内容 | 必须放哪 |
| --- | --- |
| 页面业务组件 | `pages/<module>/components/`（不放公共目录） |
| 跨页面复用组件 | `components/<domain>/` |
| SQL / 数据访问 | `core/mapper/` |
| 后端调用 | `core/ipc/` |
| 类型定义 | `types/` |
| 常量 | `core/config/` |
| 工具函数 | `utils/`（禁裸 `console.log`） |

## 3. 前端技术栈

| 维度 | 选型 | 版本 | 约束 |
| --- | --- | --- | --- |
| 框架 | React | 19.x | 函数组件 + Hooks |
| 语言 | TypeScript | 5.x+ | `strict` + `noUnusedLocals` + `noUnusedParameters`；`typecheck` 必须 0 错 0 警 |
| 构建 | Vite | 7.x | 端口固定 `1420` + `strictPort` |
| 桌面壳 | Tauri | 2.x | 路由**必须** `HashRouter`（`tauri://` 协议无 SPA fallback） |
| UI 库 | antd | 见 SKILL.md 裁决 #4（暂按 `^6`） | **必须**经 `components/ui` 封装，业务代码禁裸用 antd |
| 图标 | lucide-react | — | 统一图标库，禁混用多套 |
| 路由 | react-router-dom | v7 | `createHashRouter`，路径常量集中在 `paths.ts` |
| 状态 | Redux Toolkit + react-redux | 2.x | Redux **仅放跨页面全局状态**（如主题）；页面局部状态用 `useState` |
| 样式 | SCSS，与 tsx 严格分离 | — | 颜色/尺寸只用 CSS 变量令牌；禁内联魔法数；用 `@use` 不用 `@import` |
| 测试 | vitest | — | 与 vite 配置共用 |
| 包管理 | pnpm | — | 禁与 npm/yarn 混用同一工程 |

## 4. Rust 侧技术栈

| 维度 | 选型 | 版本 | features |
| --- | --- | --- | --- |
| 框架 | tauri | 2.x | — |
| 序列化 | serde / serde_json | 1.x | `derive` |
| 异步 | tokio | 1.x | `sync` `rt` `time` `process` |
| HTTP | reqwest | 0.12 | `json` `stream` |
| 数据库 | tauri-plugin-sql | 2.x | `sqlite` |
| 日志 | tracing / tracing-subscriber / tracing-appender | 0.1 / 0.3 / 0.2 | `env-filter` |
| 时间 | chrono | 0.4 | — |
| 工具 | regex | 1.x | 线性时间实现 |

## 5. 目录骨架

照此结构创建空目录即可（CLI 生成的骨架需按此重组）：

```text
<project>/
├─ src/                                # 前端
│  ├─ main.tsx                         # 入口：挂 RouterProvider + ConfigProvider
│  ├─ App.tsx                          # 应用壳（不含业务）
│  ├─ styles/
│  │  ├─ tokens.scss                   # 设计令牌（CSS 变量：颜色/圆角/间距/字号）
│  │  └─ global.scss                   # 全局重置 + 基础排版
│  ├─ pages/
│  │  └─ home/
│  │     ├─ index.tsx                  # 页面主文件
│  │     ├─ index.scss                 # 页面样式（与 tsx 分离）
│  │     └─ components/                # 页面私有组件（不放公共目录）
│  ├─ components/
│  │  ├─ ui/                           # UI 封装层（antd 之上）
│  │  │  ├─ index.ts                   # 统一导出入口
│  │  │  ├─ Button.tsx / Card.tsx / Modal.tsx / Input.tsx / Select.tsx
│  │  │  ├─ notify.tsx                 # useNotify() 全局消息 hook
│  │  │  └─ *.scss
│  │  └─ icons/                        # 内联 SVG 图标
│  ├─ core/
│  │  ├─ router/
│  │  │  ├─ index.tsx                  # createHashRouter + 路由表
│  │  │  └─ paths.ts                   # 路径常量（唯一来源）
│  │  ├─ ipc/index.ts                  # invoke 统一入口 + 命令名常量
│  │  ├─ mapper/*.ts                   # 数据访问层（SQL 全部在此，一模块一文件）
│  │  ├─ file/                         # 本地文件持久化（可选）
│  │  ├─ config/                       # 全局常量（APP_NAME / isTauri / API_BASE）
│  │  ├─ db/                           # 建表执行 + 连接管理（唯一 DDL 落点）
│  │  └─ store/
│  │     ├─ persistence.ts             # KV 读写封装
│  │     └─ themeSlice.ts              # 主题状态
│  ├─ types/
│  │  ├─ core.d.ts                     # 全局类型与枚举（与 Rust struct 对齐）
│  │  ├─ database.d.ts                 # 数据库行类型（与建表语句同步）
│  │  └─ shims.d.ts                    # 动态 import 库的类型补充
│  ├─ hooks/
│  └─ utils/
│     ├─ format.ts
│     └─ logger.ts                     # 日志封装（替代裸 console）
│
├─ src-tauri/
│  ├─ Cargo.toml
│  ├─ tauri.conf.json                  # 窗口、构建、devUrl
│  ├─ capabilities/default.json        # 权限声明
│  └─ src/
│     ├─ main.rs
│     ├─ lib.rs                        # 命令注册 + 插件注册 + 启动钩子
│     ├─ logging.rs                    # tracing 初始化（控制台 + 滚动文件）
│     ├─ fs_helper.rs
│     ├─ net.rs
│     └─ db.rs
│
├─ .workbuddy/memory/                  # AI 工作记忆（见 norms-and-memory.md）
├─ .workspace/.norms/                  # 项目内开发规范（事实源，同上）
├─ docs/
├─ package.json / tsconfig.json / vite.config.ts / eslint.config.js / .gitignore
```

## 6. 演进方向（未定规范，仅登记入口）

| 方向 | 引入什么 |
| --- | --- |
| 数据同步 | 后端加 HTTP 服务端 + 冲突解决策略 |
| 多窗口 | `tauri.conf.json` 配 `windows[]`，页面间用 event 通信 |
| 自动更新 | `tauri-plugin-updater` |
| 全局快捷键 | `tauri-plugin-global-shortcut` |
| 托盘常驻 | `tauri-plugin-autostart` + `TrayIcon` |
| CI/CD | GitHub Actions：`typecheck` + `cargo check` + `tauri build` |
| 国际化 | `react-i18next`，文案抽离到 locale 文件 |
