# 权限、参数、慢查询与备份恢复

## 一、账号与最小权限

**应用运行账号不得拥有 DDL 权限**，迁移与运行必须分账号。这既是等保访问控制的要求，也是事故止损：注入或误操作拿不到 `DROP`。

| 账号 | 权限 | 谁在用 |
| --- | --- | --- |
| `app_rw` | `CONNECT`、`USAGE`、目标 schema 的 `SELECT/INSERT/UPDATE/DELETE`；序列 `USAGE` | 应用进程 |
| `app_migrate` | 上述 + `CREATE/ALTER/DROP` 于**自己拥有的 schema** | Flyway 执行期，CI/发布机使用，不进应用配置 |
| `app_readonly` | 只读，指向从库 | 报表、排障、监控采集 |
| `app_audit` | 审计表 `INSERT/SELECT`，无 `UPDATE/DELETE/TRUNCATE` | 与 `security-baseline.md` 的审计防篡改要求同源 |
| 超级用户 | 不做任何业务连接 | 仅安装与应急 |

```sql
-- dialect: postgresql
CREATE ROLE app_rw LOGIN PASSWORD :'__from_env__';   -- 实际口令由发布系统注入，禁止写进脚本
GRANT CONNECT, TEMPORARY ON DATABASE app_db TO app_rw;
GRANT USAGE ON SCHEMA app TO app_rw;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA app TO app_rw;
ALTER DEFAULT PRIVILEGES IN SCHEMA app
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_rw;   -- 否则下次建表就忘了授权
REVOKE ALL ON SCHEMA public FROM app_rw;                        -- PG 15 起 public 已收紧，仍要显式确认
```

```sql
-- dialect: mysql  [MySQL 未经公司实测]
CREATE USER 'app_rw'@'10.0.%' IDENTIFIED BY '__from_env__';
GRANT SELECT, INSERT, UPDATE, DELETE, EXECUTE ON app_db.* TO 'app_rw'@'10.0.%';
-- 迁移账号只在发布窗口启用，用完即停用，不给 FILE / SUPER / PROCESS
CREATE USER 'app_migrate'@'10.0.%' IDENTIFIED BY '__from_env__';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, DROP, REFERENCES ON app_db.* TO 'app_migrate'@'10.0.%';
```

补三条：不给 `WITH GRANT OPTION`（授权传播是横向移动的入口）；`app_rw` 不持有删表能力时，删表/清理由发布脚本以 `app_migrate` 身份执行并留痕；账号口令只走环境变量，`check_secrets.sh` 负责拦截写死值。

## 二、慢查询与执行计划

上线前的取证动作，两条线都要留下计划摘要进变更单：

```sql
-- PostgreSQL：ANALYZE 会真实执行语句，涉及 DML 时在事务里跑并回滚
EXPLAIN (ANALYZE, BUFFERS, SETTINGS) SELECT ... ;

-- MySQL 8.0.18+ 同样真实执行，同样注意副作用
EXPLAIN ANALYZE SELECT ... ;
```

看三件事：**是否走预期索引**（`Index Scan` / `type=ref|range`，出现 `Seq Scan` / `type=ALL` 就是没走）、**估算行数与实际行数是否差一个数量级**（差太多先 `ANALYZE` 更新统计信息，再考虑改写）、**排序与哈希是否落盘**（`Sort Method: external merge` / `Using filesort; Using temporary` 说明 `work_mem` 不够或索引顺序不匹配）。

常驻采集：

| 目标 | PostgreSQL 16 | MySQL 8 |
| --- | --- | --- |
| 慢语句 | `log_min_duration_statement = 500`（毫秒） | `slow_query_log = 1`，`long_query_time = 1` |
| 语句级统计 | `pg_stat_statements`（需进 `shared_preload_libraries` 并重启） | `performance_schema.events_statements_summary_by_digest` |
| 未走索引的语句 | `auto_explain.log_min_duration` | `log_queries_not_using_indexes` **必须**配 `min_examined_row_limit`，否则被小表全扫刷屏 |
| 没用上的索引 | `pg_stat_user_indexes.idx_scan = 0` | `sys.schema_unused_indexes` |
| 锁等待 | `log_lock_waits = on`，`pg_locks` 查等待链 | `innodb_lock_wait_timeout` 报错 + `performance_schema.data_locks` |
| 长事务 / 空闲事务 | `pg_stat_activity WHERE state = 'idle in transaction'`，超阈值必须告警 | `information_schema.innodb_trx` 按 `trx_started` 排序 |

日常体检 SQL 见 `assets/ops/pg_health_check.sql`、`assets/ops/mysql_health_check.sql`，只读账号即可执行。

## 三、服务端参数基线

参数属于**部署契约**，必须写进 Tech Spec 的运维章节并纳入配置管理；下表是评审时用来对照"是否被改得离谱"的锚点，不是让人手工照抄。

| 方向 | PostgreSQL 16 | MySQL 8 |
| --- | --- | --- |
| 连接上限 | `max_connections`（默认 100 太小；配合应用侧池预算，`实例数 × 池max < max_connections × 0.8`），`superuser_reserved_connections = 3` | `max_connections`（默认 151），`back_log`，`thread_cache_size` |
| 内存 | `shared_buffers` 约物理内存 25%，`effective_cache_size` 50-75%（给优化器看的，不实际占用），`work_mem` 4-16MB（**每个排序/哈希节点**都算，设大易 OOM） | `innodb_buffer_pool_size` 50-70%，`tmp_table_size` / `max_heap_table_size`，`sort_buffer_size` 按连接数慎用 |
| 持久化与复制 | `wal_level = replica`，`max_wal_size`，`checkpoint_timeout`，`archive_mode` 开（否则没有 PITR） | 双 1：`innodb_flush_log_at_trx_commit = 1` + `sync_binlog = 1`；`binlog_format = ROW`，`binlog_expire_logs_seconds` |
| 优化器 | `random_page_cost = 1.1`（SSD 必改，否则偏好顺序扫描），`effective_io_concurrency = 200` | `optimizer_switch` 保持默认，索引提示优先于改优化器 |
| 语句护栏 | 按角色设 `ALTER ROLE app_rw SET statement_timeout = '30s'`、`lock_timeout = '5s'`、`idle_in_transaction_session_timeout = '60s'` | `MAX_EXECUTION_TIME`（只读语句）全局设置，`innodb_lock_wait_timeout = 10` |
| 维护 | `autovacuum` 保持开启，大表单独调低 `autovacuum_vacuum_scale_factor` | `innodb_flush_neighbors = 0`（SSD），`sql_mode` 必须含 `STRICT_TRANS_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION` |

`sql_mode` 放宽（去掉 `STRICT_TRANS_TABLES`）会让超长字符串、零日期静默截断入库，属于"用稳定性换隐蔽错误"，禁止。

## 四、备份与恢复

没有恢复演练过的备份不算备份。RPO（可丢多少数据）与 RTO（多久恢复）必须在 Tech Spec 里写明数值，并按数值选方案。

| 场景 | PostgreSQL 16 | MySQL 8 |
| --- | --- | --- |
| 逻辑全量（小库、单表恢复） | `pg_dump -Fc -Z zstd -n app app_db > app_db_$(date +%F).dump`，恢复 `pg_restore -j 4 -d app_db --single-transaction file` | `mysqldump --single-transaction --routines --triggers --events --set-gtid-purged=OFF --source-data=2 app_db > app_db_$(date +%F).sql` |
| 物理全量（大库、秒级到分钟级恢复） | `pg_basebackup -D /backup/base -Ft -z -X stream -P`，配 `archive_command` 收 WAL | XtraBackup / MCL 做热备份，配 binlog 增量 |
| 任意时间点恢复 PITR | 基础备份 + WAL 归档，`recovery_target_time` 指定时点 | 全量备份 + `mysqlbinlog --start-position=<binlog 坐标>` 重放，坐标由 `--source-data=2` 写进 dump 头 |
| 结构快照（变更前的保险） | `pg_dump --schema-only` 单独留档，变更单里贴文件名 | `mysqldump --no-data` 单独留档 |

执行要求：

1. 结构变更前**必须**先有对应范围的备份，备份产物路径、大小、时间写进变更单（D006 会检查破坏性脚本是否声明了备份）。
2. 只备份不归档等于没备份：至少一份异地、保留期按 Tech Spec（默认全量 7 天 + 30 天归档），并确认存储侧不可被应用账号删改。
3. 备份视同生产数据：含明文口令散列、手机号等个人信息，落地要加密，导出与外发按 `security-baseline.md` 的 DP-3 脱敏要求处理。审计类数据留存下限 180 天，不因"业务库要瘦身"而被顺带清掉。
4. 每季度做一次恢复演练：从备份拉起实例、跑一致性校验（行数、关键列和值、约束有效性），记录实际 RTO。演练留痕是测评与评审的共同凭证。
5. `assets/ops/backup.sh` 是可复制的最小实现，只含命令与校验，凭据一律从环境变量读取。

## 五、容量、膨胀与碎片

- **PG 表膨胀**：长事务与未清理的死元组会让表与索引虚胖，顺序扫描代价随之上升。看 `pg_stat_user_tables.n_dead_tup` 与 `last_autovacuum`，处理手段是 `VACUUM (ANALYZE)`；膨胀严重到影响读性能时用 `pg_repack` 在线整理（`TRUNCATE` 重建的代价是停写窗口）。
- **MySQL 碎片**：大量删除后 `data_free` 高，用 `OPTIMIZE TABLE`（等价重建，持锁期间不可写，必须走窗口）或在线工具。
- **增长预测**：按月统计行数与平均行长（`pg_total_relation_size` / `information_schema.TABLES.data_length + index_length`），写进容量评估。索引体积常与数据同量级，别只算数据。
- **冷热分离**：历史数据归档到新表/分区，主表保持小而热；归档走"写入新表 → 校验行数与校验和 → 分批删除原表"，禁止 `INSERT` + `DELETE` 写在同一事务里跑百万行。
