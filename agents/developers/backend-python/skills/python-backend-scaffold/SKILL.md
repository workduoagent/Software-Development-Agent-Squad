---
name: python-backend-scaffold
description: 搭建与开发 Python 3.12 + FastAPI 后端工程的通用规范与基础设施：分层结构、统一响应/错误码、JWT 与依赖注入鉴权、SQLAlchemy 2.0 + Alembic 持久层、日志链路与测试门禁。当需要新建 Python 后端项目、初始化分层结构、接入鉴权/持久层/审计，或评审 Python 后端工程时使用。不含任何业务逻辑。
---

# Python 后端工程通用 Skill

## Overview

对照 `springboot-scaffold` 的约定骨架为 Python 栈建立的初版基线：分层结构、依赖版本、公共基础设施（Result / 错误码 / 异常 / 请求上下文 / JWT / 鉴权依赖）、持久层（SQLAlchemy 2.0 + Alembic + 六大基石）、可观测性与测试门禁。
初版由仓库约定推导，尚未经生产项目提炼迭代；规范权威与 Java 侧同源——软件团队知识库《接口契约标准》《安全与日志审计基线》，本 skill 只写 Python 侧怎么实现。

## 技术栈基线

**Python 3.12** · FastAPI · SQLAlchemy 2.0（async）· Pydantic v2 · Alembic · uvicorn · python-jose（JWT）· structlog · pytest + httpx（契约镜像测试）· mypy（strict）+ ruff

## 使用方式

按任务查阅对应 reference，按需复制 assets 模板：

| 任务 | 查阅 | 可复制资产 |
| --- | --- | --- |
| 目录蓝图与分层规则 | `references/structure.md` | — |
| 配置与机密（全部走环境变量） | — | `assets/config/settings.py` 直接复制后改字段 |
| 统一响应 / 错误码 / 业务异常 | — | `assets/common/result.py` 直接复制 |
| 六大基石基类与租户索引 | — | `assets/persistence/base.py` 直接复制 |
| 等保二级安全项、审计落地（Python 侧） | `references/security.md` | — |
| 机密扫描门禁 | — | `scripts/check_secrets.py`（脚本只留在本 skill，不复制进项目） |

数据侧（连接池、DDL、迁移与回滚、PG16/MySQL8 方言、D0xx）权威在 [`database-ops/`](../database-ops/SKILL.md)，写任何 `.sql` 或数据源配置前必读。

## 核心纪律（不可违背）

1. **契约即法律**：路由路径、Pydantic 字段名与类型、响应结构与冻结契约逐字一致。改字段名 = BREAKING，必须走 architect + 总架构师流程，禁止口头改。
2. **`Result` 三键固定**：`code` / `msg` / `data`，成功码 200；路由只返回 `Result[XxxOut]`，ORM 模型出现在路由签名上即打回。
3. **错误码双向对齐**：代码枚举里每个码都要在契约 `x-error-codes` 登记；登记的码都要被错误样例用到；规则 HTTP 状态码 × 100 + 两位序号（与 Java 侧同一张登记表，不留孤儿码）。
4. **六大基石字段齐全**：`id`（雪花，禁自增）/ `created_at` / `updated_at` / `created_by` / `updated_by` / `tenant`；迁移、模型、填充三处必须一致；`tenant` 必须是某索引的前导列（database-ops D002/D003）。
5. **ID 出参字符串**：雪花 ID 逐字段序列化为字符串；**不做全局转换**，否则数量/时长也会变字符串。
6. **分层不可穿透**：router 只做契约转换与校验（鉴权与审计用依赖声明），业务与事务在 service，单表访问在 repository。
7. **`contextvars` 对称清理**：谁写请求上下文谁负责在 `finally` 里 `reset()`——协程/线程池复用下不清理会串号。
8. **鉴权不遗漏**：每个路由显式声明鉴权依赖；公开接口显式 `require_login=False`；微服务形态只信网关注入的身份 Header，服务侧不解析 JWT；两套机制不得混用。
9. **无机密入库**：配置一律 pydantic-settings 从环境变量读取；真实口令、密钥、内网地址不进仓库；缺失密钥 fail-fast 而不是给默认值。
10. **迁移只走 Alembic**：已提交脚本不可修改，语句必须幂等；改表与改模型同批提交；DDL / 连接池 / 迁移的规范权威与机检在 `database-ops`，本 skill 只保留 Python 侧接法。
11. **交付门禁**：pytest 退出码 0 + 契约镜像测试通过 + ruff / mypy strict 通过 + 机密扫描干净（`python python-backend-scaffold/scripts/check_secrets.py "{root_dir}/src"`）+ 真实日志留存文件。
12. **安全与审计即交付物**：越权两道校验（角色 + 租户与属主条件）、失败分支也记审计、敏感值脱敏后落盘（口令与 Token 完全不落）；判据见软件团队知识库 安全与日志审计基线.md；基线里标注「待总架构师拍板」的参数取值不得由开发自行假定。
13. **注释即工程产物**：禁止 emoji、图标与分隔横幅；只写功能与非显然约束，与代码同寿命；类型注解齐全。判据见软件团队知识库 开发者通用技术规范.md 第六节。
