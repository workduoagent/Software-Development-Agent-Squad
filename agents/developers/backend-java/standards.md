# Java 后端规范（Standards）

工程规范权威来源：[`skills/springboot-scaffold/`](../../../skills/springboot-scaffold/SKILL.md) —— 拓扑与分层、依赖与版本基线、统一响应与错误码、JWT 与鉴权限流、MyBatis-Plus 持久层的 Java 侧接法、日志链路、单测与交付门禁的具体规范、细节与约束全部以 Skill 为准，本文件不重复维护。

数据侧权威来源：[`skills/database-ops/`](../../../skills/database-ops/SKILL.md) —— 连接与池、DDL、DML 与修数、迁移与回滚、权限与备份恢复、PG16/MySQL8 差异与 D0xx 机检；写 `.sql` 与数据源配置以它为准。

跨技术栈通用的交付纪律权威来源：[`agents/developers/README.md`](../README.md)。

| 需要查的内容 | 去处 |
| --- | --- |
| 目录结构、单体/微服务模块拓扑 | `references/directory.md` |
| JDK 21 版本矩阵、依赖纪律、配置安全 | `references/dependencies.md` |
| Result / ErrorCodeEnum / 异常 / UserContext / JWT | `references/infrastructure.md` |
| 实体、分页填充、租户条件、mapper XML、迁移脚本在 Java 侧怎么接 | `references/persistence.md` |
| 表与索引设计、列类型、六大基石定义 | `skills/database-ops/references/ddl.md` |
| 数据变更、回填、批量、锁与并发、查询红线 | `skills/database-ops/references/dml.md` |
| 版本号与命名、在线变更、回滚、存量库接入 | `skills/database-ops/references/migration.md` |
| 连接池与 JDBC URL、超时分层、多数据源 | `skills/database-ops/references/connection.md` |
| PG 与 MySQL 差异（写脚本前先查一眼） | `skills/database-ops/references/dialect.md` |
| 鉴权与限流（单体 AOP / 微服务网关）、Nacos 配置分层 | `references/topology.md` |
| traceId 日志、单测基线、交付门禁 | `references/quality.md` |
| 审计记录落地、脱敏、登录锁定、越权两道校验、S0xx 门禁 | `references/security-audit.md`（要求本身在 `docs/02-protocols/security-baseline.md`） |

> 项目级补充约束（如特定业务域的表命名、独有的网关路由约定）在此登记，与 Skill 冲突时以 Skill 为准；
> 契约与代码基线取值不一致时（如成功响应码）不在本文件裁定，上报 architect / 总架构师后回填结论。
