# database-ops 门禁回归测试

在 `skills/database-ops/` 目录下依次执行，比对预期。脚本只做静态文本分析，不连数据库，
所以整套回归离线可跑，改完 `scripts/check_db_ops.sh` 任何一条规则都要把这四行重跑一遍。

| # | 命令 | 预期 |
| --- | --- | --- |
| 1 | `bash scripts/check_db_ops.sh assets` | `DB OPS CHECK PASSED`，exit 0，无 WARN（自带资产必须自己过线） |
| 2 | `bash scripts/check_db_ops.sh tests/fixtures/clean` | `PASSED`，exit 0，含带理由豁免的 `legacy/V9__readonly_legacy.sql` 也不报 |
| 3 | `bash scripts/check_db_ops.sh tests/fixtures/dirty` | `DB OPS CHECK FAILED`，exit 1，D001-D015 十五条码全部出现 |
| 4 | `bash scripts/check_db_ops.sh no/such/dir` | `usage: ...directory not found`，exit 2 |

## 码与夹具对应（第 3 行输出必须逐项对上）

| 码 | 触发夹具 | 触发行 |
| --- | --- | --- |
| D001 | `dirty/postgresql/V1__order_bad.sql`、`dirty/exempt/V1__reasonless_exempt.sql` | `BIGSERIAL PRIMARY KEY` |
| D002 | 同上两个 | 缺 `updated_at` / `created_by` / `updated_by`（exempt 另缺 `tenant`） |
| D003 | `dirty/postgresql/V1__order_bad.sql` | 有 `tenant` 列，唯一索引建在 `order_no` 上 |
| D004 | 同上 | `CREATE TABLE` 无 `IF NOT EXISTS`；`CREATE UNIQUE INDEX`、`ADD COLUMN` 同样缺 |
| D005 | 同上、`dirty/exempt/...` | `UPDATE` 与 `DELETE FROM` 无 `WHERE` |
| D006 | `dirty/postgresql/V1__order_bad.sql` | `TRUNCATE`，全文件没有备份产物路径与恢复命令 |
| D007 | `dirty/postgresql/...`（裸 `TIMESTAMP`）、`dirty/mysql/V1__dialect_bad.sql`（`DATETIME` 且表头无时区声明） | WARN 级 |
| D008 | `dirty/postgresql/...`（`double precision`）、`dirty/mysql/V1__dialect_bad.sql`（`DECIMAL` 无精度） | 金额列 |
| D009 | ERROR：`dirty/postgresql/...` 里的 `ON DUPLICATE KEY`、`dirty/mysql/V1__dialect_bad.sql` 里的 `ON CONFLICT` / `ILIKE` / `RETURNING` / `JSONB`；WARN：`dirty/mysql/V2__no_dialect_decl.sql` | 双向都验 |
| D010 | `dirty/naming/V2_single_underscore.sql`（命名 + 版本段两次命中）、`dirty/naming/V3__dup_a.sql` 与 `V3__dup_b.sql`（同目录重复版本） | 三类各一 |
| D011 | `dirty/mysql/V1__dialect_bad.sql` | `email VARCHAR(1000)` 进了 `uk_t_user_tenant_email` |
| D012 | `dirty/postgresql/V1__order_bad.sql` | `SELECT * FROM t_order` |
| D013 | `dirty/config/datasource-bad.yml` | ERROR：`autoReconnect=true`、`maximum-pool-size: 500`；WARN：缺 pool-name / max-lifetime / connection-timeout |
| D014 | `dirty/config/datasource-bad.yml`（两条 URL 各缺一个参数）、`dirty/postgresql/...`（加非空列无默认值） | WARN 级 |
| D015 | `dirty/exempt/V1__reasonless_exempt.sql` | 整文件豁免只列码表 + 行尾豁免只写标记，两处都要报，且被豁免的规则照常命中 |

## 夹具设计约束

- 干净夹具与资产同构：改了一条规则，先看资产还是不是绿的——资产变红说明规则改严了，要同步改文档而不是改资产迁就脚本。
- 反例夹具的注释里不要出现被检字符串本身（`timestamp`、`SELECT *`、`备份`、`恢复` 都会串台），命中说明写在码表里就够。
- `clean/legacy/` 是豁免通道的正例：`dbops-ignore` 与 `nosec-db` 都写了理由，退出码必须是 0；
  它同时验证 `serial_no` 这种列名不会被 D001 误伤。
- `dirty/exempt/` 是豁免通道的反例：理由缺失时豁免失效，D015 与原本被豁免的规则一起报。
