---
name: tauri2-scaffold
description: 搭建与开发 Tauri 2 桌面应用（React 19 + TypeScript + Rust + 本地 SQLite）的工程基线与桌面侧增量规范。当需要新建桌面工程、封装 IPC 与 Rust↔TS 类型契约、注册插件并声明 capability 权限、接入本地 SQLite、评审 WebView 路由/端口/构建坑位，或评审桌面工程结构时使用。不含通用 React 组件分层与主题体系（见 react-scaffold），不含任何业务逻辑。
---

# Tauri 2 桌面工程通用 Skill

## Overview

从桌面项目实战提炼的工程基线：技术栈取值、目录骨架、四层铁律（页面 / UI 封装 / `core/` / Rust 侧）、IPC 与类型契约、插件注册与权限双写、验证门禁、坑位速查。适用于每个新 Tauri 2 桌面工程的初始化与日常开发约束。

**本文不含业务领域设计**，只回答四个问题：用什么技术、目录长什么样、代码放哪里、怎么验证。

源文档为项目侧的《Tauri2 脚手架快速搭建方案》v1.4；进本仓库后 **`` 是唯一真源**，源文档不再单独维护，避免两处漂移。

## 适用域（先看这个，否则和 `react-scaffold` 打架）

| 工程形态 | 权威 skill |
| --- | --- |
| 纯 Web 前端（Vite + React + antd，axios 调远端服务） | `react-scaffold/`，本 skill 不适用 |
| Tauri 2 桌面（前端跑在系统 WebView，数据落本地 SQLite） | **本 skill 为主** + `react-scaffold/` 为辅 |

桌面工程下通用 React 分层（组件拆分、页面私有组件、单测四态、样式令牌语义）**指回 `react-scaffold`，本 skill 不重复维护**；只写桌面侧增量与冲突裁决。真冲突时**桌面工程以本 skill 为准**。

## 与 react-scaffold 的差异裁决

| # | 维度 | react-scaffold 基线 | 桌面方案原值 | 采信 | 理由 / 状态 |
| --- | --- | --- | --- | --- | --- |
| 1 | 路由模式 | `VITE_ROUTER_MODE` 双模式，默认 `createBrowserRouter` | 必须 `createHashRouter` | **桌面锁 hash** | `tauri://` 协议无 SPA fallback，刷新即 404。这不是选择项，是物理约束 |
| 2 | dev 端口 | 未固定 | `1420` + `strictPort` | **1420** | 必须与 `tauri.conf.json` 的 `devUrl` 对齐，端口漂移 = 白屏 |
| 3 | 后端通信与响应体 | axios + `Result<T> = {code,msg,data}` + `VITE_USE_MOCK` | Tauri `invoke` / event | **IPC 不套 `Result<T>`** | Rust `Result` 失败即 reject，再包一层 `code` 是重复表达；错误码仍须在契约与 `types/` 显式定义。**影响 QA 断言口径，待总架构师确认** |
| 4 | antd 版本 | `^6.0.0` | v5 | **暂按 `^6.0.0`** | 跨端复用 `components/ui` 封装层要求同版本；方案里的 v5 按撰写时快照处理。**待拍板** |
| 5 | 图标 | `@ant-design/icons` | `lucide-react` | **lucide-react 为主** | 两者不互斥（antd 内置图标仍可用），但业务图标只准一套 |
| 6 | 全局消息 | `FeedbackBridge` 把 `App.useApp()` 桥给 axios 拦截器 | `useNotify()` | **两个都要，分工明确** | 桌面没有 axios 拦截器，`FeedbackBridge` 无消费方；组件内一律 `useNotify()` |
| 7 | SQL 归属 | 数据访问在服务端（Java mapper） | **SQL 全在前端 `core/mapper/`** | **按桌面方案** | 桌面单机无服务端，Rust 侧只提供引擎能力。这条改变了安全基线的层次假设，见下节 |
| 8 | 样式令牌 | 三层 Sass（`variables` / `global` / `theme.css`） | `tokens.scss` 单文件 CSS 变量 | **桌面用 `tokens.scss`** | WebView 明暗切换走 `html.light` / `html.dark` + CSS 变量；令牌命名对齐 react-scaffold 语义 |

## 安全与审计基线在桌面形态下的重解释

软件团队知识库 安全与日志审计基线.md 的判据按"前端 + 远端服务"写，桌面工程不能逐字套用，映射如下（**本表是建议口径，需总架构师拍板后才是判据**）：

| 基线判据 | 桌面形态落点 |
| --- | --- |
| 二 身份鉴别 | 本地口令/生物识别由 OS 侧承担；应用内会话仍需过期与锁定阈值，取值归 §九 拍板，不得由开发假定 |
| 三 访问控制「服务端带租户与属主条件」 | **不适用**：桌面单机无服务端。等价判据改为「`core/mapper/` 每条 SQL 必须参数化绑定 + 涉及多用户目录时必须带属主过滤」 |
| 四 安全审计八要素 | 落 `tracing` 滚动日志文件（见 `references/rust-backend.md`），事件名与 Web 侧共用同一份契约清单，不得桌面另起一套 |
| 五 数据保护 | 本地 SQLite 单文件即攻击面：凭据不入库明文、不入日志；库文件路径与导出行为需明示 |
| 六 入侵防范与代码安全 | `capabilities/default.json` 最小权限 + 插件白名单等价于「不暴露多余能力面」 |
| 七 机检门禁 F0xx | 复用 `react-scaffold/scripts/check_security.sh`；S0xx 属服务端侧，桌面工程**不产出** S0xx 凭证，提测报告须写明"桌面形态，S0xx 不适用" |

## 使用方式

| 任务 | 查阅 | 可复制资产 |
| --- | --- | --- |
| 定技术栈取值、建目录骨架 | `references/stack-and-directory.md` | `assets/config/` 全部 |
| 配 `tsconfig` / `vite.config` / `tauri.conf` | `references/stack-and-directory.md` §配置要点 | `assets/config/tsconfig.json`、`vite.config.ts`、`tauri.conf.json` |
| 封装 IPC、对齐 Rust↔TS 类型 | `references/ipc-and-types.md` | `assets/core/ipc.ts` |
| 注册插件与声明权限 | `references/plugins-and-permissions.md` | `assets/src-tauri/lib.rs`、`capabilities-default.json` |
| 前端基座（入口/路由/UI 封装/令牌/消息） | `references/frontend-shell.md` | `assets/core/notify.tsx`、`assets/styles/tokens.scss` |
| Rust 侧模块与日志 | `references/rust-backend.md` | `assets/src-tauri/lib.rs` |
| 初始化工程（分阶段清单） | `references/quality-gates.md` | — |
| 交付前自检与门禁命令 | `references/quality-gates.md` | — |
| 报错排查 | `references/pitfalls.md` | — |
| 落地项目内规范目录与 AI 记忆 | `references/norms-and-memory.md` | — |

## 门禁（提测必须全绿并留日志）

```bash
npm run typecheck          # tsc --noEmit，0 error 0 warning
cd src-tauri && cargo check
npx vitest run             # 有前端单测时
bash react-scaffold/scripts/check_security.sh "{root_dir}"   # F0xx
```

🚫 调试阶段禁止手动 `npm run build`（产出 `dist*` 会污染 Tauri 的 `frontendDist` 解析）。
🚫 AI 与脚本不执行 `pnpm install` / `npm install` / `cargo add`，只登记依赖清单，装由人确认。
🚫 项目初始化 `pnpm create tauri-app` 属产品决策（命名、标识符），由人工执行，见 `references/quality-gates.md` Phase 0。

## 未覆盖清单（目前只能人工对账）

1. **插件注册完整性无机检**——`lib.rs` 用了哪些插件 vs `.plugin(...)` 实际注册，漏一个前端调用即报错。
2. **capability 最小权限无机检**——`capabilities/default.json` 声明是否过宽，无脚本判定。
3. **Rust struct ↔ `types/*.d.ts` 字段对齐无机检**——这是桌面形态最危险的坑：改了 Rust 忘了改 TS，`tsc` 全绿、运行时拿到 `undefined`。三项合起来是 Tauri 侧当前最大的机检缺口，建议后续补一个 `check_tauri_ops.sh`（占位，未实现）。
4. 自动更新、多窗口、托盘常驻、CI 打包只在 `references/stack-and-directory.md` §演进方向 列了引入项，未定规范。
5. 身份鉴别与审计留存在桌面形态下的具体取值（会话时长、锁定阈值、日志留存天数）未在 §九 拍板清单内，属空白。
6. **IPC 是否复用 Web 侧 `Result<T>{code,msg,data}` 错误码口径**——影响 QA 断言写法，未拍板前不得由开发自行假定。
7. **`csp: null` 是否可交付**——源方案默认值，建议按发布形态给出 CSP 要求，未拍板。
8. **项目 `.norms/git-commit.md` 授权工具自行 commit** 与本仓库「未获明确指示不得执行 git」的口径冲突，需二选一，未拍板。

以上 6-8 与第 5 条同属待总架构师拍板项，拍板前不得自行假定；结论回填后从本清单移除并写入对应 reference。
