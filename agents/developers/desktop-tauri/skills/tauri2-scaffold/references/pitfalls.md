# 坑位速查

按"症状能不能一眼认出来"排序。前三条是桌面工程实际卡住人最久的。

| 坑 | 症状 | 解法 |
| --- | --- | --- |
| **插件未在 `lib.rs` 注册** | 前端调用插件 API 报 `plugin not found` | `Builder` 链上显式 `.plugin(...)`，见 `plugins-and-permissions.md` |
| **只注册插件未配权限** | 报 `xxx not allowed` | `capabilities/default.json` 也要声明，两者缺一不可 |
| **Rust struct 改了前端类型没改** | 运行时拿到 `undefined`，TS **不报错** | 契约类型集中在 `types/core.d.ts`，改 Rust 必同步改（`ipc-and-types.md` §2） |
| `sql` / `store` 用 `::init()` | 编译不过 | 这两个是 Builder 模式 |
| 用了 `createBrowserRouter` | 刷新页面 404 | 改用 `createHashRouter` |
| vite 端口漂移 | Tauri 白屏连不上 | `strictPort: true` + 固定 1420，与 `devUrl` 逐字一致 |
| 调试时跑了 `npm run build` | `dist` 被锁定，tauri 启动失败 | 删 `dist`，让 tauri 自动构建 |
| 静态 `import { message } from 'antd'` | 提示不跟随主题 / 被顶栏遮挡 | 统一 `useNotify()` |
| antd 组件裸用 | 样式不统一，难以定制 | 经 `components/ui` 封装 |
| 组件直接调 `invoke` | 命令名散落难维护 | 统一走 `core/ipc` |
| CSS 硬编码颜色 | 深色模式下配色错乱 | 全部走 `var(--color-*)` 令牌 |
| `@import` 引入 scss | 控制台 deprecation 警告 | 改 `@use` |
| 建表语句写在 mapper | 多次启动重复建表报错 | 建表统一在 `core/db/` 执行 |
| `ALTER TABLE` 后占位符错位 | 运行期数据写错列，`tsc` 查不出 | 人工核对 `INSERT INTO` 三要素：列清单 / `?` 数量 / 参数数组长度 |
| `Option<T>` 当 `undefined` 处理 | 分支永不命中 | serde 默认序列化成 `null`，TS 侧写 `T \| null` |
| Rust `snake_case` vs TS `camelCase` | 字段静默 `undefined` | struct 加 `#[serde(rename_all = "camelCase")]` 并写进契约 |
| `i64` 超安全整数 | 大 id 精度丢失 | 改 `string` 传输 |
| 给根容器 `max-width` + 居中 | 宽屏两侧留白 | 一级页面根容器 `width: 100%` |
| `create-tauri-app` 走交互问答 | AI 自动化流程卡在向导 | 项目初始化交人工（`quality-gates.md` Phase 0） |
| 规范与代码冲突 | 后续改动各写各的，行为漂移 | **先改规范再改代码**，规范本身也走提交 |

## 排障顺序建议

桌面白屏/调用失败按这个顺序切，能在 3 步内定位到层：

1. `npm run tauri` 控制台有没有 Rust 侧 panic → 有则问题在 `lib.rs`（插件注册、命令未注册）。
2. devtools Console 里是 `not allowed` 还是 `not found` → 前者权限，后者注册。
3. 命令调通但数据是 `undefined` → 类型对齐问题，查 `serde` 重命名与字段名。
4. 只有刷新后坏 → 路由模式。
5. 只有端口占用时坏 → `devUrl` 与 vite 端口不一致。
