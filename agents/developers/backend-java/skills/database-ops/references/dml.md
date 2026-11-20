# 数据变更（DML）与修数

PostgreSQL 侧写法取自现网回填与修数脚本；MySQL 侧的批次语句、upsert 与批量参数本地无素材可取证，按通用工程标准与 8.0 语义编写，上线前要在真实实例上验一遍。

## 一、什么算一次数据变更

`INSERT` 初始化字典、`UPDATE` 修数、`DELETE` 清理、回填、归档、批量导入，都按变更管理，都要走变更单（`assets/templates/db_change_ticket.md`）。"只是改几行数据"是最常见的事故入口。

变更分三档，决定评审与执行方式：

| 档 | 判定 | 要求 |
| --- | --- | --- |
| 增量 | 只新增行，不动存量 | 变更单 + 机检通过 + 唯一约束防重 |
| 修改 | 更新存量行的若干列 | 追加：影响行数预查、回填与校验 SQL、可重跑、回滚方案 |
| 破坏性 | 删除、清空、覆盖不可逆字段（口令散列、外部原始值） | 追加：备份产物路径与恢复命令、总架构师批准、双人执行 |

## 二、幂等写法（D004）

同一脚本重跑必须得到相同结果。两条线的可用手段不同：

| 目的 | PostgreSQL 16 | MySQL 8 |
| --- | --- | --- |
| 建表 | `CREATE TABLE IF NOT EXISTS` | 同左 |
| 加列 | `ALTER TABLE t ADD COLUMN IF NOT EXISTS c ...` | **无此语法**：靠 Flyway 版本表保证只执行一次，或用 `INFORMATION_SCHEMA` 判断后 `PREPARE` 动态执行 |
| 建索引 | `CREATE INDEX IF NOT EXISTS` | **无此语法**：把索引内联写进 `CREATE TABLE IF NOT EXISTS` 的 `KEY` 子句；后续补索引只能裸写并在变更单声明重跑会报 1061 |
| 加约束 | 无 `IF NOT EXISTS`，用 `DO $$ ... IF NOT EXISTS (SELECT 1 FROM pg_constraint ...) ... $$` | 同 PG 思路：查 `INFORMATION_SCHEMA.TABLE_CONSTRAINTS` 后动态执行 |
| 插入防重 | `INSERT ... ON CONFLICT (cols) DO NOTHING` | `INSERT IGNORE`（会吞掉非冲突错误，慎用）或 `ON DUPLICATE KEY UPDATE id = id` |
| upsert | `INSERT ... ON CONFLICT (cols) DO UPDATE SET v = EXCLUDED.v` | `INSERT ... ON DUPLICATE KEY UPDATE v = VALUES(v)`（8.0.20 起 `VALUES()` 已废弃，改用行别名 `AS new` + `new.v`） |
| 部分唯一约束 | `CREATE UNIQUE INDEX ... WHERE is_deleted = 0` | 不支持部分索引，用 `UNIQUE (tenant, name, is_deleted)` 之类把删除标记纳入，删除时改写业务键 |

`ON DUPLICATE KEY UPDATE` 依赖"命中任一唯一键"，表上有多个唯一键时命中哪个不确定，行为比 `ON CONFLICT` 明确指定冲突目标更隐蔽——这是同一份逻辑在两条线上不等价的真实例子。

## 三、修数与回填

固定四段式，顺序不可调：

1. **预查**：`SELECT COUNT(*)` 加完全相同的 `WHERE`，把预期影响行数写进变更单。行数与预期不符就停下来，不要"先跑了再说"。
2. **执行**：`UPDATE` / `DELETE` 必须带 `WHERE`（D005 强制拦截），且 `WHERE` 走索引。大表分批，每批 1000-5000 行，批间停顿，避免长事务与主从延迟。
3. **校验**：脚本末尾留校验 SQL 并以注释说明期望结果，例如剩余未回填行数必须为 0。现网 `mcp_scope_system_to_default.sql:37-40` 就是这个做法，保留。
4. **回滚**：能反向写的写反向语句；不能反向写的（覆盖原值）必须先备份受影响行的原值。

分批写法：

```sql
-- PostgreSQL：无 UPDATE ... LIMIT，用 ctid/主键子查询限定批次
UPDATE biz_project SET stage = 'ACCEPTED'
WHERE id IN (SELECT id FROM biz_project WHERE stage = 'DELIVERING' ORDER BY id LIMIT 2000);
```

MySQL 支持 `UPDATE ... WHERE ... ORDER BY id LIMIT 2000`，但 `ORDER BY` 只对单表更新有效且必须有主键顺序；两条线的分批语句**不能互相复制**，脚本要按方言各写一份。

新列回填的标准三步（大表必须这样，见 `migration.md` 第二节）：先加**可空**列 → 分批回填 → 再 `ALTER` 加 `NOT NULL`/默认值约束。一条 `ALTER TABLE ... ADD COLUMN x NOT NULL DEFAULT ...` 在 PG 11+ 不重写整表（可以放心），在 MySQL 8 的 `INSTANT` 算法下也便宜，但**存量行的语义**仍要在变更单里说清。

## 四、批量写入

| 手段 | 说明 |
| --- | --- |
| 多值 `INSERT` | 一条语句 500-1000 行为宜。过大触发 `max_allowed_packet`（MySQL）/ 参数个数上限（PG 单语句 65535 个绑定参数），且长事务放大回滚段 |
| MyBatis-Plus `saveBatch` | 必须配 JDBC 参数才真正合并：MySQL `rewriteBatchedStatements=true`，PG `reWriteBatchedInserts=true`（`connection.md` 第三节）。缺省配置下逐条发送，是"批量比单条循环快不了多少"的根因 |
| PG `COPY` | 十万级以上导入的最快路径，走 `CopyManager`；注意它不触发 `DEFAULT` 之外的隐式填充，`created_at` 等仍要显式给 |
| 禁止 | 循环单条 `insert`（N 次往返）、循环单条 `update`、把一批变更塞进一个跨分钟级的大事务 |

## 五、锁与并发

1. 事务要短。**禁止**在事务里做 RPC、发消息、读文件、等锁之外的任何慢操作。长事务在 PG 侧还会挡住 vacuum，导致表膨胀。
2. 悲观锁必须**走索引**：`SELECT ... FOR UPDATE WHERE id = ?`。MySQL 里不带索引的 `FOR UPDATE` 会升级成范围/全表锁并持到事务提交，是生产锁等待的头号成因。两条线都支持 `NOWAIT` 与 `SKIP LOCKED`（PG 9.5+ / MySQL 8.0+），任务队列取活用 `SKIP LOCKED` 而不是自造抢占标记。
3. 更新计数用 `SET n = n + 1` 让数据库原子完成（现网 `AgentInfoServiceImpl.java:373` 即如此），不要"读-改-写"。读改写必须有 `version` 乐观锁兜底。
4. 多行更新按**固定顺序**（如主键升序）加锁，交叉顺序是死锁模板。
5. 死锁是可预期成本：捕获死锁错误码（PG `40001`、MySQL `1213`）后**重试整个事务**，而不是重试失败的那条语句。重试次数要有上限与退避。
6. `REPLACE INTO`（MySQL）本质是先删后插：未列出的列会丢、自增值跳号、触发器多跑一轮。除幂等覆盖写小表外不要用。

## 六、删除与清理

- 物理删除前列出**引用方**：哪些表存了它的外键语义列（哪怕没有外键约束）、哪些缓存与搜索引擎需要同步清理。现网零外键 + 跨数据源物理删除（`KnowledgeChunksMapper.xml:59-64`）留下孤儿记录，是已确认缺陷。
- 大批量清理走"新表换名"或分区裁剪：`INSERT INTO t_clean SELECT ...` → `ALTER TABLE ... RENAME`（或 `EXCHANGE PARTITION`），比 `DELETE` 上百万行快几个数量级，且不产生长事务。MySQL `TRUNCATE` 是 DDL 且隐式提交、会重置自增值；PG `TRUNCATE` 可在事务内回滚且支持 `RESTART IDENTITY CASCADE`，两者不可互换理解。
- 任何 `DELETE` / `TRUNCATE` / `DROP` 在生产执行前必须有可恢复备份（D006 要求脚本写明备份产物路径）。

## 七、查询侧红线

1. 禁止 `SELECT *`（D012）：列变动会让结果映射静默出错、拿不到覆盖索引收益、宽行拖爆网络。
2. 分页必须 `ORDER BY` 一个**唯一确定的键组合**（通常追加 `id`），否则翻页会重复或漏行。列表返回 `{total, list}`，`total` 用独立 `COUNT` 或 `COUNT(*) OVER()`，不允许内存分页。
3. `IN` 列表上限：超过几千个元素改临时表 join 或 `= ANY(ARRAY[...])`（PG）。MySQL 侧 `IN` 过多会影响优化器选择，批量阈值经验值 1000。
4. `OR` 连接不同列会让索引失效，改 `UNION ALL` 或分别建索引后合并。
5. 隐式类型转换会绕开索引：字符串列与数字比较、`varchar` 时间列做范围比较（PG 上 `timestamp` 与 `varchar` 比较还会因排序规则不同给出错误结果）。列类型与参数类型必须一致。
6. 慢查询上线前必须看执行计划（`operations.md` 第二节），"本地快就行"不成立：数据量与统计信息都不同。
