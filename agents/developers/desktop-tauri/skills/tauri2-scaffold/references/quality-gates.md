# 门禁与搭建执行清单

## 1. 验证门禁（提测必须全绿并留日志）

```bash
npm run typecheck                 # tsc --noEmit，0 error 0 warning
cd src-tauri && cargo check       # 必须通过
npx vitest run                    # 有前端单测时
bash react-scaffold/check_security.sh "{root_dir}"   # F0xx 前端安全机检
```

- 🚫 **禁止提交带 typecheck error**——编译器是唯一裁判。
- 🚫 **调试阶段禁止手动 `npm run build`**——产出 `dist*` 目录会污染 Tauri 的 `frontendDist` 解析，症状是 `tauri dev` 起不来。
- 🚫 禁止留 `console.log`，统一走 `utils/logger.ts`。
- 门禁命令与退出码逐条写进提测报告，日志重定向到文件并给物理路径（软件团队知识库 开发者通用技术规范.md 第三节骨架）。

## 2. 依赖管理

- 新增依赖只登记进 `package.json` / `Cargo.toml`。
- **AI 与脚本不执行** `pnpm install` / `npm install` / `cargo add`——由人确认后执行。
- 避免引入多个同类库（3 个 UI 库、3 个图标库这类）。

## 3. 注释规范

只写**为什么**（约束、陷阱、性能原因），不写**是什么**：

```ts
// ✅ 解释原因
// offsetWidth 不含边框，用 getBoundingClientRect 避免 1px 误差
const width = el.getBoundingClientRect().width

// ❌ 叙述代码
// 获取元素宽度
const width = el.offsetWidth
```

与软件团队知识库 开发者通用技术规范.md 第六节同源，桌面工程不另立标准。

## 4. 提交规范

- 一个语义一个提交，格式 `<type>(<scope>): <中文主题>`，type ∈ `feat` `fix` `refactor` `chore` `docs` `test`。
- 提交前必须过验证门禁。
- 不提交密钥、`.env`、`node_modules`、构建产物。
- **push 永远归用户本人**，工具只 commit（与软件团队知识库 开发者通用技术规范.md 及本仓库既有约定一致）。

## 5. 搭建执行清单

> 前置约定：本清单从「项目已存在」开始。

### Phase 0 · 项目初始化（人工，一次性）

```bash
pnpm create tauri-app
```

向导选择：`Rust` + `pnpm` + `React` + `TypeScript`。

`create-tauri-app` 支持非交互参数（`--manager pnpm --template react-ts --identifier com.mycompany.myapp --tauri-version 2 --yes`），但**不建议 AI 主动执行**：项目命名与标识符属产品决策，且该命令会安装依赖、写入大量文件，应由人主导。

CLI 生成骨架与本清单有出入时（Vite 端口、TS 配置项），以 `frontend-shell.md` §1 的配置要求为准覆盖。

### Phase 1 · 基线对齐（约 30 分钟）

- [ ] 核对 `package.json` scripts，缺失则补
- [ ] 登记业务依赖：`react react-dom react-router-dom antd @reduxjs/toolkit react-redux lucide-react @tauri-apps/api` + 所需插件（只写清单，装由人）
- [ ] 登记开发依赖：`typescript vite @vitejs/plugin-react sass @types/react @types/react-dom vitest`
- [ ] 按 `stack-and-directory.md` §5 建完整目录（CLI 骨架需重组）
- [ ] 落地 `.workspace/.norms/` 四份规范（见 `norms-and-memory.md`）
- [ ] 初始化 `.workbuddy/memory/MEMORY.md`
- [ ] 配 `tsconfig.json` / `vite.config.ts`（端口必须 1420 + `strictPort`）
- [ ] 按 `plugins-and-permissions.md` 在 `lib.rs` 注册所有用到的插件
- [ ] 配 `capabilities/default.json` 权限声明
- [ ] Rust 侧依赖入 `Cargo.toml`，`cargo check` 通过
- [ ] 跑一次 `npm run tauri`，确认原始工程能启动（基线可用再改造）

### Phase 2 · 前端基座（约 1 小时）

- [ ] `styles/tokens.scss` + `global.scss`
- [ ] `components/ui/`：`Button` `Card` `Modal` `Input` `Select` `Tag` + `notify.tsx` + `index.ts`
- [ ] `core/router/`（`paths.ts` + `index.tsx`）
- [ ] `core/ipc/index.ts`
- [ ] `core/config/index.ts`（`APP_NAME` / `isTauri`）
- [ ] `utils/logger.ts` + `utils/format.ts`
- [ ] 占位页 `pages/home/`，跑通路由跳转
- [ ] `npm run typecheck` EXIT 0

### Phase 3 · 后端基座（约 1 小时）

- [ ] `logging.rs`（tracing 初始化）
- [ ] `lib.rs`：注册 `ping` 探活命令 + 显式注册所有插件
- [ ] `fs_helper.rs` + `net.rs`
- [ ] `capabilities/default.json` 配插件权限（注册 ≠ 授权）
- [ ] `cargo check` 通过
- [ ] `npm run tauri` 启动，窗口正常，devtools 无报错

### Phase 4 · 数据层接入（约 1 小时，可选）

- [ ] `core/db/`：建表执行 + 连接管理
- [ ] 第一个 mapper `core/mapper/example-mapper.ts`
- [ ] Rust 侧接口类型与 `types/core.d.ts` **逐字段核对一致**
- [ ] 验证读写链路正常
- [ ] 写 `types/database.d.ts`

### Phase 5 · 交付前检查

- [ ] `npm run typecheck` 0 error 0 warning
- [ ] `cargo check` 通过
- [ ] `npm run tauri` 启动无控制台报错
- [ ] 目录结构与 `stack-and-directory.md` §5 一致
- [ ] `lib.rs` 中所有用到的插件均已注册
- [ ] `capabilities/default.json` 已声明对应权限
- [ ] 前端接口类型与 Rust `struct` 字段逐一对齐
- [ ] 无 `console.log` 残留
- [ ] 无硬编码色值（全部 `var(--color-*)`）
- [ ] `README.md` 写明启动方式

> 工期口径：Phase 1–4 的「30 分钟 / 1 小时」是方案原值的**净开发时间**，不含联调、验收与返工。
