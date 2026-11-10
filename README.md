# Software-Development-Agent-Squad

An autonomous multi-agent team orchestrated for end-to-end software development, from requirement breakdown to contract-driven delivery.

> **进度说明**：协议层（契约标准、安全与审计基线、验收判据）、`contract_validator`、`react-scaffold`、`springboot-scaffold`、`database-ops`
> 及 `pm` / `architect` / `backend-java` / `frontend-react` 四个角色已落地并实测；
> `task_tracker`、`artifact_inspector`、`orchestration/workflow.yaml`、QA 与 python / rust 角色仍为占位，待填充。

## 团队角色

| 角色 | 目录 | 职责 |
| --- | --- | --- |
| 项目经理 (PM) | `agents/pm/` | 需求澄清、任务拆解与分派、验收把关 |
| 总架构师（人类） | 由用户担任 | 技术选型拍板、契约与破坏性变更决策 |
| 系统架构师 (Architect) | `agents/architect/` | 总架构师的技术副官：Tech Spec、DDL、OpenAPI 契约产出，contract_validator 校验与指纹锁定 |
| Java 后端工程师 | `agents/developers/backend-java/` | JDK 21, Spring Boot 3, MyBatis-Plus；数据侧 PostgreSQL 16 / MySQL 8 双方言（单体 / 微服务两种拓扑）|
| Python 后端工程师 | `agents/developers/backend-python/` | FastAPI / Flask, SQLAlchemy, pytest |
| Rust 后端工程师 | `agents/developers/backend-rust/` | Actix / Axum, Tokio, cargo test |
| React 前端工程师 | `agents/developers/frontend-react/` | React, Vite, TypeScript, Vitest/MSW |
| 质检工程师 (QA) | `agents/qa/` | 物理制品与测试日志验证、验收 |

> 全体成员（含 PM 与 Architect）共同遵守 [`docs/02-protocols/security-baseline.md`](docs/02-protocols/security-baseline.md)：
> 等保二级为默认基线，功能 + 安全控制项 + 门禁脚本真实通过三者齐备才算交付。

## 目录结构

```
Software-Development-Agent-Squad/
├── README.md                     # 项目全景概览、设计哲学与团队架构图
├── docs/                         # 【设计与孵化全过程记录】
│   ├── 00-manifesto.md           # 团队愿景、协作原则与设计纪律（人设总则）
│   ├── 01-architecture.md        # 多智能体协同拓扑、状态机模型与流转图
│   ├── 02-protocols/             # 交互协议规范（契约优先标准）
│   │   ├── task-schema.json      # 任务分派与生命周期标准（六要素定义）
│   │   ├── api-contract-spec.md  # 接口契约标准（OpenAPI/JSON Schema 约定 + 安全与审计的契约侧声明）
│   │   ├── security-baseline.md  # 安全与日志审计基线（等保二级，全项目唯一权威来源）
│   │   └── review-criteria.md    # 物理验收标准与打回机制（含安全与审计人工判据）
│   └── changelog/                # 智能体迭代与孵化日记（记录调优过程与踩坑）
│
├── agents/                       # 【核心智能体工坊：每个角色的独立家园】
│   ├── pm/                       # 项目经理 (Project Manager)
│   │   ├── prompt.md             # 核心 System Prompt
│   │   ├── tools.md              # 依赖与授权的 Skill / MCP 说明
│   │   └── examples/             # 拆解与分派任务的标准示例（Few-Shot）
│   ├── architect/                # 系统架构师 (Architect)：总架构师（用户）的技术副官
│   │   └── prompt.md             # 核心 System Prompt（Tech Spec / DDL / OpenAPI 契约产出与校验）
│   ├── developers/               # 🌟【开发人员大类】
│   │   ├── README.md             # 开发者通用交付纪律（所有语言开发必须遵守的底线）
│   │   ├── backend-java/         # Java 后端工程师 (JDK 21, Spring Boot 3, MyBatis-Plus, PG16 / MySQL 8)
│   │   │   ├── prompt.md
│   │   │   └── standards.md      # 指向 skills/springboot-scaffold/ 与 skills/database-ops/ 的角色侧索引
│   │   ├── backend-python/       # Python 后端工程师 (FastAPI / Flask, SQLAlchemy, pytest)
│   │   │   ├── prompt.md
│   │   │   └── standards.md
│   │   ├── backend-rust/         # Rust 系统/后端工程师 (Actix / Axum, Tokio, cargo test)
│   │   │   ├── prompt.md
│   │   │   └── standards.md
│   │   └── frontend-react/       # React 前端工程师 (React, Vite, TypeScript, Vitest/MSW)
│   │       ├── prompt.md
│   │       └── standards.md
│   └── qa/                       # 质检工程师 (QA / Test Engineer)
│       ├── prompt.md
│       └── test-rubrics.md       # 验证与验收判据细则
│
├── orchestration/                # 【智能体编排与工作流定义】
│   ├── workflow.yaml             # 协同流程定义（或 LangGraph / CrewAI / 自研管道配置）
│   └── state_machine.md          # 任务在各角色间单向流转的状态机定义
│
├── skills/                       # 【赋予智能体的专属技能与工具实现】
│   ├── task_tracker/             # 看板与任务持久化工具 (PM 用)
│   ├── contract_validator/       # 契约校验、Diff 与指纹锁定工具 (architect 用，PM 核验凭证)
│   ├── artifact_inspector/       # 物理文件与测试日志质检脚本 (PM / QA 用)
│   ├── react-scaffold/           # React 前端通用开发 skill (frontend-react 用)
│   │   ├── references/           # 目录/依赖/基础设施/路由布局/样式/测试/安全落地细则
│   │   ├── assets/               # 配置、核心基础设施、样式、测试模板
│   │   └── scripts/check_security.sh  # 前端安全机检门禁 F001–F008
│   ├── springboot-scaffold/      # Java 后端通用开发 skill (backend-java 用，含单体/微服务两套拓扑资产)
│   │   ├── references/           # 目录/依赖/基础设施/持久层 Java 接法/拓扑/质量/安全与审计细则
│   │   ├── assets/               # 配置、公共组件、安全、异常、审计、网关、测试模板
│   │   └── scripts/check_security.sh  # 后端安全机检门禁 S002–S008、S010
│   └── database-ops/             # 数据侧通用开发 skill (backend-java 用，architect 出 DDL 骨架时查)
│       ├── references/           # 连接与池 / DDL / DML 与修数 / 迁移与回滚 / 权限与备份 / 方言差异
│       ├── assets/               # 双方言建表与回填模板、回滚样例、数据源配置片段、体检与备份脚本、变更单模板
│       ├── scripts/check_db_ops.sh     # 数据库变更机检门禁 D001–D015
│       └── tests/                # clean / dirty 夹具与 run_tests.md 回归表
│
└── templates/                    # 【交付制品模版库（供智能体引用）】
    ├── prd-template.md           # 需求澄清模版
    ├── tech-spec-template.md     # 技术规格模版
    └── task-dispatch-template.json # 标准任务派发 Payload 模版
```