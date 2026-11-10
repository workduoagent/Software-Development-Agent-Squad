---
name: database-ops
description: PostgreSQL 16 与 MySQL 8 的数据连接、表结构（DDL）、数据变更（DML）、迁移与回滚、账号权限与备份恢复的权威规范，含双方言差异对照表和数据库变更机检脚本 check_db_ops.sh（D0xx）。当需要设计表或索引、写迁移与回填脚本、配置数据源与连接池、定备份恢复方案、排查慢锁，或评审一份 DDL/数据变更是否可上线时使用。不含 Java 实体与 ORM 用法，那部分见 skills/springboot-scaffold/references/persistence.md。
---

# 数据库操作通用 Skill（PostgreSQL 16 / MySQL 8）

## Overview

公司两条数据库线：**PostgreSQL 16**（新项目默认，现网 we-agent-cloud、we-oa、ai-explaner-server 全部是 PG）与 **MySQL 8**（存量与外部对接）。本 skill 是**数据侧唯一权威**：连接与池、表与索引、数据变更、迁移与回滚、权限与备份恢复、门禁脚本。

**本 skill 的取材边界（评审时必须知道）**：

- PostgreSQL 部分从现网项目取证（列名、幂等写法、索引补齐、`COMMENT ON` 习惯均有真实文件可查）。
- MySQL 8 部分**本地代码库零素材**（全仓 `mysql-connector` / `mysql:8` / `jdbc:mysql` 命中为 0），按通用工程标准与 MySQL 8.0 官方语义编写，凡标注 `[MySQL 未经公司实测]` 的条款，落库前需在真实实例上验证一遍再固化。
- 现网列名实际是 `create_at` / `update_at`，基线裁定统一为 **`created_at` / `updated_at`**（见 A2 结论）。存量库不改名，由实体侧列映射适配。

## 技术栈基线

| 项 | PostgreSQL 线 | MySQL 线 |
| --- | --- | --- |
| 版本 | 16.x（下限 13，`IF NOT EXISTS` 与 `ON CONFLICT` 全可用） | 8.0.x（下限 8.0.16，`CHECK` 与 `EXPLAIN ANALYZE` 才真正生效）[MySQL 未经公司实测] |
| 驱动 | `org.postgresql:postgresql` 42.7.3 | `com.mysql:mysql-connector-j` 8.4.0 [MySQL 未经公司实测] |
| 字符集/排序 | `UTF8` + `database` collation，默认**大小写敏感** | `utf8mb4` + `utf8mb4_0900_ai_ci`，默认**大小写不敏感** |
| 时间存储 | `TIMESTAMPTZ`（UTC 存储） | `DATETIME(3)`（无时区，靠连接时区口径统一） |
| 迁移工具 | Flyway 10.17（DDL 可在事务内回滚） | Flyway 10.17（**DDL 隐式提交，失败不可回滚**，见 `migration.md` 第四节） |

两条线的**逻辑模型必须一致**：表名、列名、语义、索引意图相同，只允许类型与语法按方言落地。同一项目内不得混用两种方言，脚本按文件头的 `-- dialect:` 声明判定（`check_db_ops.sh` D009）。

## 使用方式

| 任务 | 查阅 | 可复制资产 |
| --- | --- | --- |
| 配数据源、定连接池、排连接泄漏 | `references/connection.md` | `assets/config/datasource-postgres.yml`、`datasource-mysql.yml` |
| 设计表、列类型、约束与索引 | `references/ddl.md` | `assets/postgresql/V1__example_baseline.sql`、`assets/mysql/V1__example_baseline.sql` |
| 写回填、批量、upsert、修数 | `references/dml.md` | `assets/postgresql/backfill_example.sql`、`assets/mysql/backfill_example.sql` |
| 版本化迁移、灰度加列、回滚 | `references/migration.md` | `assets/postgresql/U1__rollback_example.sql` |
| 建账号、授权、备份恢复、慢查询 | `references/operations.md` | `assets/ops/pg_health_check.sql`、`assets/ops/mysql_health_check.sql`、`assets/ops/backup.sh` |
| 提交一份变更（任何 DDL/DML） | `references/dialect.md` 对照表 + 变更单 | `assets/templates/db_change_ticket.md` |

## 六条硬约束（命中即打回，不接受"线上先这样"）

1. **业务主键由应用生成雪花 ID**：`BIGINT` 裸列。禁 `SERIAL` / `BIGSERIAL` / `GENERATED AS IDENTITY` / `AUTO_INCREMENT`（D001）。分库分表下自增必然撞号，且 ID 会泄露体量。
2. **六大基石列齐备且 `tenant` 有索引**：`id` / `created_at` / `updated_at` / `created_by` / `updated_by` / `tenant`，`tenant` 必须是某索引的前导列（D002、D003）。租户隔离是越权防线，不是可选项。
3. **脚本必须可重复执行**：PG 用 `IF NOT EXISTS` 全家桶，约束与索引缺该语法时用 `DO` 块补齐；MySQL 无 `ADD COLUMN IF NOT EXISTS`，索引内联进 `CREATE TABLE IF NOT EXISTS`，其余靠版本号 + 变更单里的"重跑后果"说明（D004）。
4. **改数据必带条件、先备份、后校验**：`UPDATE`/`DELETE` 无 `WHERE` 直接拦（D005）；`DROP` / `TRUNCATE` / 删列必须同脚本写明备份产物路径与恢复命令（D006）；回填脚本末尾必须留校验 SQL。
5. **金额与 ID 不用浮点，时间不用无时区裸列**：金额 `NUMERIC(p,s)` / `DECIMAL(p,s)`（D008）；PG 用 `TIMESTAMPTZ`，MySQL 用 `DATETIME(3)` 且在表头声明时区口径（D007）。现网 `TIMESTAMP` 无时区 + 应用侧 `GMT+8` 是已确认的跨时区缺陷，不得复制。
6. **未评审的 schema 不进生产**：任何 DDL/DML 变更必须附 `assets/templates/db_change_ticket.md` 填全的变更单，含预估行锁影响、执行窗口、回滚方案、校验结论；`bash skills/database-ops/scripts/check_db_ops.sh <目录>` 退出码 0 是提测与上线的共同前置。

## 交付门禁

```bash
bash skills/database-ops/scripts/check_db_ops.sh <sql或配置目录>   # 0 通过；1 有 ERROR；2 目录不存在
```

| 码 | 级别 | 判定 | 依据 |
| --- | --- | --- | --- |
| D001 | ERROR | 主键用了 SERIAL / IDENTITY / AUTO_INCREMENT | ddl.md 第一节 |
| D002 | ERROR | 建表块缺六大基石列 | ddl.md 第二节 |
| D003 | ERROR | 有 `tenant` 列但没有以它为前导列的索引 | ddl.md 第五节 |
| D004 | ERROR | 建表/建索引/加列缺幂等写法 | dml.md 第二节 |
| D005 | ERROR | `UPDATE` / `DELETE FROM` 无 `WHERE` | dml.md 第三节 |
| D006 | ERROR | `DROP` / `TRUNCATE` 未写明备份产物与恢复命令 | migration.md 第五节 |
| D007 | WARN | PG 用裸 `TIMESTAMP`；MySQL 用 `DATETIME` 但表头没声明时区口径 | ddl.md 第三节 |
| D008 | ERROR | 金额列用浮点或无精度 DECIMAL | ddl.md 第三节 |
| D009 | ERROR / WARN | 声明方言里出现对方言专有语法；未声明方言 | dialect.md |
| D010 | ERROR | Flyway 文件名非法或同目录版本号重复 | migration.md 第一节 |
| D011 | WARN | MySQL utf8mb4 索引键长超 3072 字节风险 | ddl.md 第五节 |
| D012 | WARN | `SELECT *` | dml.md 第七节 |
| D013 | ERROR / WARN | `autoReconnect=true`、池上限超 100、池关键参数缺失 | connection.md 第二节 |
| D014 | WARN | URL 缺 `socketTimeout` / `rewriteBatchedStatements`；加非空列未带默认值 | connection.md 第三节、migration.md 第二节 |
| D015 | ERROR | 豁免只列码表或只写标记，没写理由 | 本节 |

覆盖 D001-D015，机检的是**脚本里写得出来的东西**。查不出的部分归人工评审：索引是否真命中查询、执行窗口是否避开高峰、回滚是否在演练环境跑过、大表 `ALTER` 的锁影响评估——按 `references/ddl.md` 第六节与 `references/migration.md` 第五节的清单逐条签认。

豁免两种写法，都必须带理由，否则脚本判**豁免不生效并报 D015**（与 `security-baseline.md` 的 nosec 纪律同源）：

| 写法 | 作用域 | 说明 |
| --- | --- | --- |
| 行尾 `-- nosec-db: 理由` | 单行 | 无 WHERE 的语句把标记写在同一行分号之后即可被识别 |
| 文件头 `-- dbops-ignore: D002,D003 理由` | 整个文件 | 存量表接入用，理由要写清排期或工单号 |

三条例外要说在前面：D006 是文件级判定（备份路径与恢复命令写在脚本任意位置就算，行尾标记对它无效）；D001 / D002 / D003 / D005 / D006 的豁免理由必须是可追责的排期或工单，"历史遗留"不算理由；脚本只查有没有写理由，理由是否成立由评审判。

## 常见坑（都是真实代价）

- PG 不给外键列自动建索引，MySQL InnoDB 建了——迁移到 PG 的表若漏加 join 列索引，查询直接退化成顺序扫描。
- `CREATE INDEX CONCURRENTLY` 不能在事务里跑，失败会留下 `INVALID` 索引，必须先 `DROP INDEX` 再重建；Flyway 里要单独关掉该脚本的事务。
- MySQL 的 DDL 隐式提交：一条 `ALTER` 失败等于半个 schema 落地，只能靠备份恢复，不能靠事务回滚。
- MySQL 默认 `utf8mb4_0900_ai_ci` 让 `'Abc' = 'abc'` 为真，PG 默认不成立。用户名、编码类唯一约束在两条线上行为不同，测试数据要分别覆盖。
- 连接池 `maxLifetime` 必须小于数据库/代理侧的空闲回收（MySQL `wait_timeout` 默认 28800s、RDS Proxy 与 PgBouncer 常设 5-15min），否则高峰期出现"拿到已死连接"的间歇报错。
- 多数据源不是分布式事务：现网 nexus 的 business/vector 两套 DS 各有事务管理器，一个 `@Transactional` 包不住两边，删除链路会留孤儿记录。跨 DS 一致性只能靠补偿设计，禁止假定回滚会传播。
- 把连接池参数全塞进配置中心（现网 we-agent-cloud 即如此）会让**数据连接契约脱离代码评审**：仓库里查不到任何 `hikari` 键。基线要求结构与默认值进 `application.yml`，只有 host 与凭据走环境变量。

## Resources

- `references/`：连接与池 / DDL / DML / 迁移与回滚 / 运维与备份 / 双方言对照表
- `assets/`：双方言建表与回填模板、回滚脚本样例、数据源配置片段、数据库体检 SQL、备份脚本、变更单模板
- `scripts/check_db_ops.sh`：D0xx 机检门禁
- `tests/fixtures/`：`clean/` 干净样本（含带理由的豁免示范）与 `dirty/` 反例集合，`tests/run_tests.md` 是脚本的回归表
