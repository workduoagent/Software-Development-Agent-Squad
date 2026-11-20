# 表结构设计（DDL）

PostgreSQL 侧条款取自现网库表与迁移脚本；MySQL 侧的类型与索引写法本地无素材可取证，按通用工程标准与 8.0 语义编写，首次落库要在真实实例上验一遍。

## 一、命名与形态

| 对象 | 规则 | 例 |
| --- | --- | --- |
| 表 | 小写下划线，业务域前缀，单数或团队既定的集合名 | `biz_project`、`sys_api_key` |
| 列 | 小写下划线 | `contract_date` |
| 主键 | `pk_{表}` | `pk_biz_project` |
| 唯一约束 | `uk_{表}_{语义}` | `uk_biz_project_tenant_name` |
| 普通索引 | `idx_{表}_{列}` | `idx_biz_project_tenant_stage` |
| 检查约束 | `ck_{表}_{语义}` | `ck_biz_project_kind` |

PostgreSQL 侧**一律不加双引号**：不加引号的标识符折叠为小写，一旦某处用了 `"Biz_Project"`，之后每条不带引号的 SQL 都找不到它，报错还提示"关系不存在"。MySQL 侧的 `lower_case_table_names` 在不同部署（Linux 默认 0、Windows 默认 1）不一致，所以表名一律小写，不依赖服务器设置。

每个脚本文件头三行固定，`check_db_ops.sh` 靠它判定方言与留存口径：

```sql
-- 表：biz_project（业务-项目）
-- dialect: postgresql        # postgresql | mysql，同一目录内不得混用（D009）
-- 幂等：可重复执行            # 说明重跑后果，或写明由 Flyway 版本表保证
```

## 二、六大基石

| 列 | 类型（PG） | 类型（MySQL） | 约束 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `BIGINT` | `BIGINT` | `PRIMARY KEY`，无默认值 | 应用侧雪花 ID 生成，禁止数据库自增与序列 |
| `created_at` | `TIMESTAMPTZ` | `DATETIME(3)` | `NOT NULL DEFAULT` 当前时间 | 创建时间 |
| `updated_at` | `TIMESTAMPTZ` | `DATETIME(3)` | `NOT NULL DEFAULT`，MySQL 另加 `ON UPDATE CURRENT_TIMESTAMP(3)` | 更新时间 |
| `created_by` | `BIGINT` | `BIGINT` | 可空 | 创建人；系统任务为 `NULL`，不写 0 冒充用户 |
| `updated_by` | `BIGINT` | `BIGINT` | 可空 | 更新人 |
| `tenant` | `BIGINT` | `BIGINT` | `NOT NULL DEFAULT 0` | 租户 ID，0 为系统保留租户；必须有前导索引 |

列顺序固定为"主键、六大基石、业务列"，让 diff 与评审一眼看出结构漂移。现网 `create_at` / `update_at` 是历史拼写，存量库**不改名**（改名是 BREAKING，要走数据变更流程），由实体侧 `@TableField("create_at")` 映射；新库一律用基线列名。

可选列只在契约里真有对应语义时才加，加了就得承担它的义务：

- `is_deleted SMALLINT NOT NULL DEFAULT 0`（软删除）：所有查询必须带 `is_deleted = 0`，且唯一约束要把 `is_deleted` 或删除时间纳入，否则删除后无法重建同名记录。现网 we-agent-cloud 零软删除、41 处物理删除，这类决定必须在 Tech Spec 里写明。
- `version INTEGER NOT NULL DEFAULT 0`（乐观锁）：必须配 MyBatis-Plus `@Version`，否则它只是一个永远为 0 的列。

## 三、类型选择

| 语义 | PostgreSQL 16 | MySQL 8 | 禁止 |
| --- | --- | --- | --- |
| 主键 / 外键 ID | `BIGINT` | `BIGINT` | `INT`（雪花装不下）、`VARCHAR` 存 ID（索引膨胀，除对外编码外不用） |
| 金额 | `NUMERIC(14,2)` | `DECIMAL(14,2)` | `FLOAT` / `DOUBLE` / `REAL` / PG `MONEY`（D008） |
| 状态 / 枚举 | `SMALLINT` + `CHECK` 或字典表 | `SMALLINT` + `CHECK`（8.0.16 起生效） | `ENUM`（加值即 DDL，且跨方言不可移植） |
| 短文本 | `VARCHAR(n)`，n 按业务上限取 | 同左 | `TEXT` 当默认（无长度约束、无法直接索引、`SELECT *` 拖包） |
| 长文本 | `TEXT` | `TEXT` / `LONGTEXT` 按上限取 | `VARCHAR(4000)` 硬顶 |
| 半结构化 | `JSONB`（可 GIN 索引） | `JSON`（索引需生成列 + 索引该列） | 把稳定字段塞进 JSON（契约无法声明） |
| 时间 | `TIMESTAMPTZ` | `DATETIME(3)` | `TIMESTAMP`（MySQL 有 2038 上限且隐式时区转换；PG 裸 `TIMESTAMP` 无时区） |
| 日期 | `DATE` | `DATE` | 用 `VARCHAR` 存 `2026-11-10` |
| 布尔 | `BOOLEAN` | `TINYINT(1)` + 0/1 | MySQL `BIT`（驱动与前端序列化都别扭） |
| 精确小数比率 | `NUMERIC(10,4)` | `DECIMAL(10,4)` | 浮点算百分比后累加 |

宽度取值要按业务上限而不是"统一给 255"：`VARCHAR(255)` 与 `VARCHAR(32)` 在 PG 里存储开销相同，但在 MySQL 里影响索引键长上限与内存临时表判定，且宽度本身就是约束声明。

## 四、约束与默认值

1. `NOT NULL` 是默认要求。可空列必须能说清"空"与"零/空串"的区别，否则一律 `NOT NULL DEFAULT`。现网大量列可空又无默认，导致应用侧到处判空。
2. 默认值写在数据库里，不只写在实体上：`DEFAULT 0`、`DEFAULT CURRENT_TIMESTAMP`。只靠 ORM 填充的列，被运维手工插入或迁移脚本回填时就会是 `NULL`。
3. `CHECK` 用于封闭取值域（状态、类型），PG 与 MySQL 8.0.16+ 都真正强制。历史库补 `CHECK` 时先 `NOT VALID` 再 `VALIDATE`，避免一条脏数据锁住全表（见 `migration.md` 第三节）。
4. **外键默认不建**。多实例写入与后续分库成本高于它带来的保护，一致性由 service 层与唯一约束保证；但**不建外键不等于不建索引**：所有 join 列（`project_id`、`kb_id`、`asset_id` 之类）必须有索引。PG 不会替外键列自动建索引，这是现网踩过的坑。团队若决定建外键，必须在 Tech Spec 里写明并由 `ddl` 评审确认删除顺序与级联策略。
5. 唯一约束要带租户维度：`(tenant, 业务键)`，而不是裸业务键。跨租户同名是合法数据。

## 五、索引设计

| 规则 | 理由 |
| --- | --- |
| `tenant` 必须是某索引的前导列（D003 强制） | 几乎所有查询都带租户条件，前导列错位会直接退化为顺序扫描 |
| 复合索引按"等值列在前、范围列在后、排序列其次"排列 | `WHERE tenant=? AND stage=? ORDER BY created_at DESC` 对应 `(tenant, stage, created_at DESC)` |
| 只在建索引能改变执行计划时建 | 每个二级索引都抬高写入放大与vacuum压力；低基数列（状态、是否删除）单独建索引通常无用，PG 上改用部分索引 |
| 高频只读查询做覆盖索引 | `INCLUDE` / 复合列覆盖可让 PG 走 index-only scan，避免回表 |
| 长文本索引：PG 用 `pg_trgm` GIN 或表达式索引 `lower(col)`；MySQL 用前缀索引 | MySQL `utf8mb4` 单列索引键上限 3072 字节，即约 768 字符，超了必须写前缀长度（D011 WARN）；PG 的 `LIKE '%x%'` 用 btree 无效 |
| 大小写不敏感需求显式实现 | MySQL `*_ai_ci` 默认排序规则天然不敏感，PG 必须 `citext` 或 `lower()` 表达式索引，否则同名唯一性两条线行为不同 |
| 部分索引处理软删除与热点子集 | PG `CREATE INDEX ... WHERE is_deleted = 0`；MySQL 不支持，只能把 `is_deleted` 放进复合索引前导条件 |
| 表达式/函数索引两边都能用但写法不同 | PG `CREATE INDEX ON t (lower(name))`；MySQL 8 需先建 `GENERATED ALWAYS AS` 列再索引该列 |

## 六、DDL 人工评审清单（脚本查不出的部分，逐条签认）

1. 这张表的**写入来源**是谁，是否只有本服务写；多服务共写一张表需要总架构师确认。
2. **数据量与增速**预估：一年后行数、单行宽度、索引后体积，决定分区与归档策略。超过千万行的表必须在此处说明清理方案。
3. 索引是否有**对应查询**支撑。列出每条索引目标查询的 `EXPLAIN (ANALYZE, BUFFERS)` / `EXPLAIN ANALYZE` 结论，贴执行计划摘要，不接受"以后会用到"。
4. 是否存在**大表 ALTER**：加列/改类型/加索引的锁影响是否已评估，是否安排在变更窗口，是否给出在线方案（见 `migration.md` 第二节）。
5. 列的**取值域与来源**是否与契约一致：状态枚举值、金额精度、ID 是否对外序列化为字符串。
6. 是否**可回滚**：删列/删表在两条线上的代价不同（MySQL DDL 隐式提交，PG 事务内可回滚），回滚脚本是否真实存在并演练过。
7. 备份与恢复点是否已确认（改结构前必须有可恢复的备份，见 `operations.md` 第四节）。
8. 是否影响**从库/下游同步**：`binlog` 订阅、CDC、数仓抽数的表结构变更需下游确认。
