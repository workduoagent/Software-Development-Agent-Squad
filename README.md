# Software-Development-Agent-Squad

契约优先的多智能体软件开发小分队：从需求澄清、任务派发、契约冻结到物理验收的本地文件驱动流水线。

## 设计原则

1. **状态只属于 PM**：任务账本、状态机、派发、验收、打回与汇报全部由 PM 独占；architect、开发者与 QA 只接收任务输入、产出物理制品与凭证，不读账本、不判状态、不参与流程。
2. **技能随角色走**：每个角色只使用自己目录下的 `skills/`，共用技能按角色各持一份副本；仓库根 `skills/` 是由 `scripts/sync_skills.py` 生成的只读视图，供插件打包使用，不手改、不进 git。命令里的脚本以 skill 名开头（如 `task_tracker/validate.py`），agent 挂载技能后按技能根寻址。
3. **规范按软件团队知识库引用**：规范类文档（安全基线、契约标准、验收判据、模版、通用技术规范等）统一由软件团队知识库管理，平铺存放，文件名即文档名（如 `安全与日志审计基线.md`）；角色 prompt 只写「请查阅软件团队知识库 文档名.md」，绑定知识库的智能体自行检索，不绑定仓库物理路径，也不需要名实映射表。项目运行时产物写在任务卡的 `root_dir` 下。工具命令中的路径（`--schema`、skill 名开头的脚本路径）是运行时参数，不属于知识引用。
4. **角色真源唯一**：`agents/**/prompt.md` 是角色正文的唯一来源；其余文档只做索引与细则，不另立一套角色定义。

## 团队角色

| 角色 | 目录 | 职责 |
| --- | --- | --- |
| 项目经理 (PM) | `agents/pm/` | 需求定界、任务拆解派发、契约冻结登记、物理验收、状态流转、三段式汇报；唯一编排者 |
| 总架构师（人类） | 由用户担任 | 技术选型拍板、契约与破坏性变更决策、安全参数与豁免审批 |
| 系统架构师 (Architect) | `agents/architect/` | Tech Spec、DDL 骨架、OpenAPI 契约产出与机器校验凭证 |
| Java 后端工程师 | `agents/developers/backend-java/` | JDK 21 + Spring Boot 3，PostgreSQL 16 / MySQL 8 双方言 |
| Python 后端工程师 | `agents/developers/backend-python/` | Python 3.12 + FastAPI，SQLAlchemy 2.0 + Alembic，pytest（初版基线） |
| 脚本工程师 | `agents/developers/script-python/` | Python 自动化脚本与一次性工具：可复现、幂等、无机密（散活为主） |
| Rust 后端工程师 | `agents/developers/backend-rust/` | Actix / Axum、Tokio、cargo test（占位稿，无技能不派生产任务） |
| React 前端工程师 | `agents/developers/frontend-react/` | React 19 + Vite + antd，契约类型镜像与 Mock 联调 |
| Tauri 2 桌面工程师 | `agents/developers/desktop-tauri/` | Tauri 2 + React 19 + Rust + 本地 SQLite，`src/` 与 `src-tauri/` 双责任面 |
| 质检工程师 (QA) | `agents/qa/` | 集成/端到端与安全用例，产出可复现的测试报告与日志 |

## 目录结构

```
Software-Development-Agent-Squad/
├── README.md                     # 全景概览、设计原则与分发说明
├── tasks.json                    # 中央账本，PM 单写，不随插件分发
├── agents/                       # 角色工坊，每个角色的独立家园
│   ├── pm/
│   │   ├── prompt.md             # 角色正文 + 合并进来的账本/验收/流程规程
│   │   ├── orchestration/        # PM 专用的操作手册（状态机已进知识库）
│   │   │   └── workflow.yaml     # 阶段 S0-S8、门禁命令、人工闸门（PM 手工执行，无执行器）
│   │   └── skills/
│   │       ├── task_tracker/     # 账本校验、看板、派发检查、流转、契约登记
│   │       └── artifact_inspector/ # 产出物、日志、摘录与副作用核验
│   ├── architect/
│   │   ├── prompt.md
│   │   └── skills/
│   │       ├── contract_validator/ # Lint、Diff、指纹、Mock 生成
│   │       └── database-ops/       # 数据侧规范与 D0xx 门禁
│   ├── developers/
│   │   ├── backend-java/  { prompt.md, skills/springboot-scaffold, skills/database-ops }
│   │   ├── backend-python/ { prompt.md, skills/python-backend-scaffold, skills/database-ops }
│   │   ├── script-python/  { prompt.md, skills/python-scripting }
│   │   ├── backend-rust/  { prompt.md }  # 占位
│   │   ├── frontend-react/ { prompt.md, skills/react-scaffold }
│   │   └── desktop-tauri/ { prompt.md, skills/tauri2-scaffold, skills/react-scaffold }
│   └── qa/
│       ├── prompt.md
│       └── skills/{artifact_inspector,contract_validator}
├── 软件团队知识库/              # 10 份规范文档录入底稿，文件名即知识库文档名，可整目录上传
├── QoderWaker/                  # QoderWake 数字员工部署装配包（角色三件套/知识库/WakerFlow 底稿/实例与环境档案）
├── skills/                       # 生成视图，由 scripts/sync_skills.py 从各角色技能扁平化
└── scripts/
    ├── sync_skills.py            # 扁平化生成 + 同名副本一致性校验
    ├── install_agents.py         # 安装角色 prompt 为用户级 Agent
    ├── package_plugin.py         # 装配插件包，技能从角色目录汇总
    └── package_waker.py          # 打包 QoderWake 上传工作台目录 + 增量重传清单
```

## 制品链

需求 → 设计 → 契约 → 实现 → 验证各留一份可登记制品，前一份是后一份的唯一输入，跨节引用一律用节号：

```
docs/prd-v{N}.md        PM    ← 软件团队知识库 PRD 模版.md       业务事实、权限口径、待拍板事项
  → docs/tech-spec.md   architect ← 软件团队知识库 Tech Spec 模版.md 选型、属主条件、基线映射、拍板取值
  → contracts/*.yaml    architect ← contract_validator 校验 + PM 登记冻结（tasks.json 项目 contracts 表）
  → 代码与迁移脚本       developers ← 冻结契约（Inputs 带 version + sha256）
  → qa/reports + logs   QA    ← 冻结契约 + Tech Spec 拍板值
```

`docs/prd-v{N}.md` 与 `docs/tech-spec.md` 属项目制品，写在 `root_dir` 下，不进本仓库 `artifact_inspector` 的回归范围。

## 技能真源与扁平视图

技能真源位于各角色目录，例如 `agents/architect/contract_validator/`。同名技能（如 `database-ops`）在多个角色下各有一份副本；副本必须逐字节一致。

```bash
python scripts/sync_skills.py --check   # 只校验副本一致性
python scripts/sync_skills.py           # 生成仓库根 skills/ 视图
```

命令与 skill 内部脚本一律以 skill 名开头（如 `task_tracker/validate.py`、`react-scaffold/scripts/check_security.sh`），agent 挂载技能后按技能根寻址，不需要人工代入路径。skill 真源在角色目录下，插件打包时由 `scripts/sync_skills.py` 扁平化；同名副本冲突则打包失败。

## 分发：作为 Qoder Plugin 安装

本仓库自身是插件源，`.qoder-plugin/plugin.json` 声明 `skills`。`scripts/package_plugin.py` 把角色技能扁平化进插件根 `skills/`，再装配为可安装产物：

```bash
python scripts/package_plugin.py        # → dist/software-development-agent-squad/ 与 ...-0.3.0.zip
```

装配排除中央账本 `tasks.json`、`.idea/`、`.git/`、`dist/` 以及 **`agents/` 整目录**。最后一条来自装机实测：Qoder 安装器按约定递归加载 `agents/` 下每个 `.md` 为 Agent 定义，缺 YAML frontmatter 即报 `plugin.agent.invalid` 并整包失败，与 `plugin.json` 是否声明 `agents` 无关。角色进入客户端走下一节。

装机后脚本位于插件目录 `~/.qoder-cn/plugins/cache/local/software-development-agent-squad/<version>/skills/`，由插件打包时扁平化生成；开发态则是本仓库根 `skills/`。两处脚本相对路径写法一致。`{ledger}` 始终指向克隆到本地的仓库根 `tasks.json`。只装插件、未克隆仓库的机器无法运行 PM（`{ledger}` 无处解析）。

版本纪律：只在仓库里改，改完递增 `plugin.json` 的 `version`，重新打包并安装；不在客户端安装目录里就地编辑。实测边界：下划线技能名可被运行时解析（限定名 `<插件名>:<技能目录名>`，不看 SKILL.md 的 `name`）；卸载只更新 `plugins/installed_plugins_v2.json`，不清 `plugins/cache/local/<name>/` 空壳，也不回收 `settings.json` 的 `enabledPlugins` 键；递增版本号的原地升级会回收旧版本目录，并同步 `installPath`。

## 分发：作为自定义智能体安装

角色不进插件，改用用户级 Agent 目录直装：

```bash
python scripts/install_agents.py --dry-run   # 先看落盘计划
python scripts/install_agents.py             # 写入 ~/.qoder-cn/agents/<name>.md
```

脚本只复制、不改写；真源是 `agents/**/prompt.md`，frontmatter 写在 `prompt.md` 里。判定规则：**带 YAML frontmatter 的 `prompt.md` 才安装**，其余文档跳过，`backend-rust` 占位稿自动落在 SKIP。覆盖同名 Agent 前旧文件备份到 `%TEMP%\agent-install-backup\<时间戳>.<name>.md`。

当前落地 8 个：项目经理、系统架构师、Java 后端工程师、Python 后端工程师、脚本工程师、React 前端工程师、Tauri2 桌面工程师、质检工程师。

运行时事实（实测）：

- `~/.qoder-cn/agents/**/*.md` 递归扫描，文件名不是关键、frontmatter 的 `name` 才是显示名；新文件放进去即注册，无需重启。
- 覆盖同名文件时 `agentId` 不变；正文改动要等下一个刷新周期才反映到 `definitionRevision`，核验装机态以新建会话为准。
- 缺 frontmatter 的文件不毁掉整目录扫描，这与插件安装器"一个坏文件整包失败"不同。
- `skills:` 只认块列表，flow 式写法被静默忽略；限定名沿用 `<插件名>:<技能目录名>`。
- `usageScopes` 与 `model` 不吃文件覆盖，要改走设置界面或 `manage_app_agent update`。

技能挂载按各角色 prompt 的 frontmatter 配：

| Agent | skillRefs |
| --- | --- |
| 项目经理 | `task_tracker`, `artifact_inspector` |
| 系统架构师 | `contract_validator`, `database-ops` |
| Java 后端工程师 | `springboot-scaffold`, `database-ops` |
| React 前端工程师 | `react-scaffold` |
| Tauri2 桌面工程师 | `tauri2-scaffold`, `react-scaffold` |
| 质检工程师 | `artifact_inspector`, `contract_validator` |

## 已知缺口

编排层的完整缺口清单（无执行器、PRD/Tech Spec 无内容校验器、REQ 追溯、契约 §八 无机检、并发写账本无锁、QA 覆盖率无法机检）已归档到 `软件团队知识库/任务状态机.md`，随设计决策一起维护，此处不再重复。
