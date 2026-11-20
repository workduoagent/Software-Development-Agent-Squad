# PostgreSQL 16 与 MySQL 8 差异对照

同一份逻辑模型要在两条线上落地，差异集中在下面这张表。移植时**逐行对照**，不要凭另一条线的直觉写。带 `[MySQL 未经公司实测]` 的行需在真实 8.0 实例上验证。

## 一、行为语义（不是语法问题，最容易埋 bug）

| 主题 | PostgreSQL 16 | MySQL 8 | 基线要求 |
| --- | --- | --- | --- |
| 默认隔离级别 | `Read Committed` | `REPEATABLE READ`（间隙锁生效） | 跨线业务不依赖隔离级别隐含行为；需要"读已写一致"显式加锁或走同一连接事务 |
| 语句重读可见性 | 同事务内每条语句看到最新已提交数据 | 同事务内普通 `SELECT` 读快照，改了才看得见自己 | 计数器、状态机推进一律 `SET x = x + 1`，不读改写 |
| 大小写比较 | 默认**区分**大小写 | `utf8mb4_0900_ai_ci` 默认**不区分** | 用户名等大小写敏感字段：PG 用 `citext` 或 `lower()` 表达式索引 + 唯一约束；测试数据必须同时含 `Abc` / `abc` [MySQL 未经公司实测] |
| 尾部空格 | `char(n)` 填充比较，`varchar` 不忽略 | `VARCHAR` 比较忽略尾部空格（`PAD SPACE` 类排序规则；`0900_ai_ci` 改为 NO PAD，行为与 PG 更接近） | 入库前 trim，禁止依赖比较行为 |
| 空串与 `NULL` | `''` 与 `NULL` 不同 | 同左（不同于 Oracle） | 状态列禁 `NULL`，用默认值 |
| 整数除法 | `5/2 = 2`（同） | `5/2 = 2.5000`（精确除法） | 比例计算显式 `::numeric` / `CAST` ，别指望 `/` 语义一致 |
| DDL 事务性 | 可回滚 | 隐式提交 | 见 `migration.md` 第四节，一条 MySQL 脚本只做一件事 |
| 自增与序列 | `SERIAL` / `IDENTITY` 背后是序列 | `AUTO_INCREMENT` | 两者都**禁止**用于业务主键（D001），主键由应用生成 |
| 外键索引 | 不自动为 FK 建索引 | InnoDB 自动建 | 不建 FK，但 join 列必须显式建索引（`ddl.md` 第五节） |
| 时间存储 | `TIMESTAMPTZ` 存 UTC，按会话时区显示 | `DATETIME` 无时区；`TIMESTAMP` 有 2038 与隐式转换问题 | PG 用 `TIMESTAMPTZ`；MySQL 用 `DATETIME(3)` + 固定 `connectionTimeZone`（D007） |
| 触发器/存储过程 | 函数体系（`plpgsql`），DDL 可在其中 | 语法受限多、调试难 | 业务逻辑放应用层；库内只允许维护触发器做 `updated_at` 兜底 |

## 二、语法对照（写脚本时查这张表）

| 目的 | PostgreSQL 16 | MySQL 8 |
| --- | --- | --- |
| upsert | `INSERT ... ON CONFLICT (a,b) DO UPDATE SET v = EXCLUDED.v` | `INSERT ... AS new ON DUPLICATE KEY UPDATE v = new.v` |
| 插入忽略 | `ON CONFLICT DO NOTHING` | `INSERT IGNORE` 或 `ON DUPLICATE KEY UPDATE id = id` |
| 加列（存在则跳过） | `ADD COLUMN IF NOT EXISTS` | 无此语法：`INFORMATION_SCHEMA.COLUMNS` 判断 + `PREPARE` 动态执行 |
| 建索引（存在则跳过） | `CREATE INDEX IF NOT EXISTS` | 无此语法：索引内联进 `CREATE TABLE`，或接受重时报 1061 |
| 加约束（存在则跳过） | 无 `IF NOT EXISTS`，用 `DO $$ ... pg_constraint ... $$` | 无，同 `INFORMATION_SCHEMA` 思路 |
| 在线加索引 | `CREATE INDEX CONCURRENTLY`（不能在事务内） | `ALTER TABLE ... ADD INDEX ..., ALGORITHM=INPLACE, LOCK=NONE` |
| 限行更新 | 无 `UPDATE ... LIMIT`：用主键子查询 | `UPDATE ... ORDER BY id LIMIT n`（仅单表） |
| 返回受影响行 | `INSERT/UPDATE/DELETE ... RETURNING id` | 无 `RETURNING`，用 `ROW_COUNT()` |
| 截断表 | `TRUNCATE t RESTART IDENTITY CASCADE`（可回滚） | `TRUNCATE t`（DDL，隐式提交，重置自增） |
| 字符串拼接 | `a \|\| b` | `CONCAT(a, b)`（`\|\|` 默认是逻辑或，`PIPES_AS_CONCAT` 未开） |
| 模糊 + 不区分大小写 | `col ILIKE '%x%'` | `col LIKE '%x%'`（依赖 ci 排序规则） |
| 全文/包含索引 | `pg_trgm` GIN、`tsvector` GIN | `FULLTEXT` 索引 + `MATCH ... AGAINST` |
| 正则 | `col ~* 'pattern'` | `REGEXP_LIKE(col, 'pattern', 'i')` |
| 分组连接 | `string_agg(col, ',' ORDER BY id)` | `GROUP_CONCAT(col ORDER BY id SEPARATOR ',')`（受 `group_concat_max_len` 截断） |
| 日期截断 | `date_trunc('day', ts)` | `DATE_FORMAT(dt, '%Y-%m-%d')` / `DATE(dt)` |
| 时区换算 | `ts AT TIME ZONE 'Asia/Shanghai'` | `CONVERT_TZ(dt, '+00:00', '+08:00')`（需时区表已载入） |
| 类型转换 | `col::numeric`、`text = any($1)` | `CAST(col AS DECIMAL)`；无 `ANY(数组)`，改 `IN (...)` |
| 数组 / 复合类型 | 原生支持 `TEXT[]`、记录类型 | 不支持，改 JSON 或关联表 |
| JSON 取值 | `col->>'k'`、`col#>>'{a,b}'`，索引走 `JSONB` + GIN | `col->>'$.k'`（等价 `JSON_UNQUOTE(JSON_EXTRACT())`），索引需生成列 + 二级索引 |
| 部分/条件索引 | `CREATE INDEX ... WHERE is_deleted = 0` | 不支持，把标记列纳入复合索引 |
| 函数索引 | `CREATE INDEX ON t (lower(name))` | 8.0 需先建 `GENERATED ALWAYS AS (lower(name)) STORED` 列再索引 |
| 取前 N 行 | `LIMIT n OFFSET m` | `LIMIT m OFFSET n` 或 `LIMIT n OFFSET m`（都支持） |
| 窗口函数 | 完整（9.4 起） | 8.0 起支持；5.7 及以前没有——存量 5.7 实例不可用 |
| 布尔字面量 | `TRUE` / `FALSE` | 无布尔类型，用 `1` / `0`（`BOOLEAN` 是 `TINYINT(1)` 别名） |
| 主键聚簇 | 表默认堆表，索引非聚簇 | InnoDB 主键即聚簇索引，插入顺序影响碎片 |
| 元数据查询 | `information_schema` + `pg_catalog`（`pg_indexes`、`pg_stat_user_tables` 更实用） | `information_schema` + `mysql.*` + `performance_schema` |
| 批量导入 | `COPY`（服务端）/ `\copy`（客户端） | `LOAD DATA LOCAL INFILE`（需 `local_infile=1`，且是安全审查项） |

## 三、驱动与连接参数差异

| 项 | PostgreSQL | MySQL |
| --- | --- | --- |
| 批量合并开关 | `reWriteBatchedInserts=true` | `rewriteBatchedStatements=true` |
| 读超时 | `socketTimeout`（秒，默认 0 不超时） | `socketTimeout`（毫秒，默认 0 不超时） |
| 建连超时 | `connectTimeout`（秒） | `connectTimeout`（毫秒） |
| 时区 | `options=-c timezone=...` 或 SQL `SET TIME ZONE` | `connectionTimeZone` + `forceConnectionTimeZoneToSession` |
| 服务端预编译 | `prepareThreshold`（默认 5） | `useServerPrepStmts` + `cachePrepStmts` |
| TLS | `sslmode=verify-full` + `sslrootcert` | `sslMode=VERIFY_IDENTITY` + `trustCertificateKeyStore` |
| 认证插件 | `scram-sha-256`（PG 默认，勿再配 md5） | `caching_sha2_password`（8.0 默认，非 TLS 首连需 `allowPublicKeyRetrieval`） |

## 四、方言选择的既有事实

- 需要 `JSONB` 索引、向量检索（pgvector）、全文/模糊匹配、数组列、部分索引 → **PostgreSQL**。现网 we-agent-cloud 正是这三类（JSONB + pgvector + `pg_trgm`）。
- 只涉及常规 CRUD、且要接的第三方系统只支持 MySQL → **MySQL 8**，并在 Tech Spec 里承认上面这些能力缺口。
- 一个业务域内不要双库并存：跨库没有事务，一致性只能靠补偿（现网 nexus 的 business/vector 双 DS 已付出代价，见 `connection.md` 第五节）。
