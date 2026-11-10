---
name: springboot-scaffold
description: 搭建与开发 JDK 21 + Spring Boot 3 后端工程的通用规范与基础设施，覆盖单体与微服务（Nacos + Spring Cloud Alibaba）两种拓扑。当需要新建后端项目、初始化分层结构、装配统一响应/错误码/JWT/鉴权限流/MyBatis-Plus+PostgreSQL/Flyway/日志链路，或评审后端工程与表结构时使用。不含任何业务逻辑。
---

# Java 后端工程通用 Skill

## Overview

从两个生产项目（微服务 `we-agent-cloud`、单体 `ai-explaner-server`）整合提炼的后端工程基线：分层结构、依赖版本、公共基础设施（Result / 错误码 / 异常 / 上下文 / JWT / 鉴权切面）、持久层（MyBatis-Plus + PostgreSQL + 六大基石 + Flyway）、可观测性与测试门禁。

一套基线 + 两种拓扑变体，**不拆成两个 skill**：`common` / `persistence` / `quality` 完全共用，只在 `topology.md` 里按单体或微服务分叉鉴权与配置方式。

## 技术栈基线

**JDK 21（公司既定，不可下调）** · Spring Boot 3.3.4 · Maven · MyBatis-Plus 3.5.6 · PostgreSQL 42.7 · Flyway 10.17 · JJWT 0.12.6 · Redisson 3.31 · Lombok · JUnit 5 + Mockito

微服务追加：Spring Cloud 2023.0.3 + Alibaba 2023.0.3.2（Nacos 注册与配置、Gateway/WebFlux、OpenFeign）

## 使用方式

按任务查阅对应 reference，按需复制 assets 模板：

| 任务 | 查阅 | 可复制资产 |
| --- | --- | --- |
| 选拓扑、建目录与分层 | `references/directory.md` | `assets/config/pom-*.xml` |
| 定依赖版本、配置安全自查 | `references/dependencies.md` | `assets/config/application.yml`、`bootstrap-nacos.yml`、`logback-spring.xml` |
| 统一响应 / 错误码 / 异常 / 上下文 / JWT | `references/infrastructure.md` | `assets/common/`、`assets/security/`、`assets/exception/` |
| 实体、分页、自动填充、租户条件构造 | `references/persistence.md` | `assets/persistence/BaseEntity.java`、`assets/config/Mybatis*.java`；建表脚本与迁移规范见 [`skills/database-ops/`](../database-ops/SKILL.md) |
| 鉴权与限流（单体 AOP / 微服务网关） | `references/topology.md` | `assets/aspect/`（单体）、`assets/gateway/` + `assets/web/` + `assets/config/WebMvcConfig.java`（微服务） |
| 日志 traceId、单测、交付门禁 | `references/quality.md` | `assets/web/RequestTraceFilter.java`、`assets/testing/`、`scripts/check_secrets.sh` |
| 等保二级安全项、日志审计落地 | `references/security-audit.md` | `assets/audit/`、`assets/testing/Audit*Test.java`、`scripts/check_security.sh` |

`scripts/check_secrets.sh`（S001 机密）与 `scripts/check_security.sh`（S002–S008、S010）是可执行门禁（`bash scripts/check_xxx.sh src`），退出码 0 才算干净，可直接进 CI。安全与审计**要求本身**只有一份：`docs/02-protocols/security-baseline.md`，本 skill 只写 Java 侧怎么实现。

## 核心纪律（不可违背）

1. **契约即法律**：接口字段名、错误码、分页参数一律以冻结契约为准。改字段名 = BREAKING，必须走 architect + 总架构师流程，禁止口头改。
2. **`Result` 三键固定**：`code` / `msg` / `data`，成功码 200；Controller 只能返回 `Result<XxxVO>`，entity 出现在接口签名上即打回。
3. **错误码双向对齐**：代码枚举里每个码都要在契约 `x-error-codes` 登记（E006），登记的码都要被错误样例用到（E011）；规则是 HTTP 状态码 × 100 + 两位序号。
4. **六大基石字段齐全**：`id`（雪花，禁自增）/ `created_at` / `updated_at` / `created_by` / `updated_by` / `tenant`（单列索引）。DDL、BaseEntity、FillHandler 三处必须对得上。
5. **ID 出参字符串**：雪花 ID 逐字段 `@JsonSerialize(ToStringSerializer)`；**不做全局 Long→String**，否则数量/时长也会变字符串，前端算术全错。
6. **分页方言写死**：`PaginationInnerInterceptor(DbType.POSTGRE_SQL)` + `maxLimit(500)` + `overflow(false)`；`updateFill` 用 `setFieldValByName`，`insertFill` 用 `strictInsertFill`。
7. **ThreadLocal 对称清理**：谁写 `UserContext` 谁负责 finally / `afterCompletion` 里 `remove()`——JDK 21 虚拟线程 + 线程池复用下不清理就会串号。
8. **鉴权不遗漏**：单体每个 mapping 方法必须 `@ApiRegister`（公开接口显式 `requireLogin = false`）；微服务网关必须 `mutate` 覆盖身份 Header，服务侧不再解析 JWT。
9. **无机密入库**：yml / 代码里不得出现真实口令、密钥、内网 IP、namespace UUID；缺失密钥要 fail-fast 而不是给默认值。
10. **结构变更只走 Flyway**：已提交脚本不可修改，语句必须幂等；改表和改实体在同一任务里提交。DDL / DML / 连接池 / 迁移的规范权威与机检脚本都在 [`skills/database-ops/`](../database-ops/SKILL.md)，本 skill 只保留 Java 侧接法。
11. **交付门禁**：`mvn clean verify` 退出码 0 + 单测全绿并留存真实日志 + 无机密命中（`check_secrets.sh`）+ 无安全 ERROR 命中（`check_security.sh`）+ 契约镜像测试通过；本次改动含 `.sql` 或数据源配置时，`check_db_ops.sh` 退出码 0 同为前置；`e.printStackTrace()`、真实网络/DB 进单测一律打回。
12. **安全与审计即交付物**：等保二级的开发侧控制项（鉴权与锁定、越权两道校验、参数化 SQL、脱敏、审计记录）与功能同任务交付，判据与门禁编号见 `docs/02-protocols/security-baseline.md`；基线里标注"待总架构师拍板"的参数取值不得由开发自行假定。
13. **注释即工程产物**：禁止 emoji、图标与 `====` / `----` 分隔横幅；只写功能与非显然约束，与代码同寿命。判据见 `agents/developers/README.md` 第六节。

## 拓扑选择速判

| 信号 | 拓扑 |
| --- | --- |
| 单业务域、单团队、一份库 | **单体**（默认） |
| 需独立发布 / 多语言服务 / API-Key 开放平台 | **微服务** |
| 说不清 | 单体，运维成本要由总架构师在冻结契约前确认 |

## assets 落位对照

| 资产 | 复制到 |
| --- | --- |
| `common/{Result,ErrorCodeEnum,BusinessException,UserContext}.java` | `${base-package}.common` |
| `security/{JwtUtils,JwtProperties,JwtConfig}.java` | `${base-package}.security` |
| `exception/GlobalExceptionHandler.java` | `${base-package}.exception` |
| `persistence/BaseEntity.java` | `${base-package}.pojo` |
| `config/{MybatisPlusConfig,MybatisPlusFillHandler,WebMvcConfig}.java` | `${base-package}.config` |
| `aspect/{ApiRegister,ApiRegisterAspect}.java` | 单体：`${base-package}.aspect` |
| `gateway/AuthGlobalFilter.java` | 微服务：`app-server-gateway` |
| `web/{UserContextInterceptor,InternalTokenInterceptor,RequestTraceFilter}.java` | 微服务：`app-core-web` / 单体：`${base-package}.web` |
| `audit/{AuditEventType,AuditLog,AuditRecorder,AuditLogAspect,SensitiveMaskUtils}.java` | `${base-package}.audit`（详见 `references/security-audit.md`） |
| `testing/*.java` | `src/test/java/...`（改名与断言按实际契约） |

复制后检查：包名 `com.example` 全局替换为项目 `${base-package}`；`ErrorCodeEnum` 补业务码段；
`BaseEntity` 若接旧库需改 `@TableField` 列名；`application.yml` 的 `type-aliases-package` 跟随包名。
