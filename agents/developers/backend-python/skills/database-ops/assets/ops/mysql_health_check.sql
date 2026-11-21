-- MySQL 8 体检：只读账号即可执行 [MySQL 未经公司实测，首次使用需在真实实例上验证列名与权限]
-- dialect: mysql
-- 用法：mysql --defaults-file=~/.my.cnf app_db < mysql_health_check.sql
-- 依赖：performance_schema 与 sys schema 开启；缺权限的语句单独跳过并在排障记录里注明

-- 1 连接水位与来源分布
SHOW VARIABLES LIKE 'max_connections';
SELECT count(*) AS total_threads
FROM performance_schema.threads WHERE type = 'FOREGROUND';

SELECT SUBSTRING_INDEX(host, ':', 1) AS client_host,
       user, db, count(*) AS conns
FROM information_schema.processlist
GROUP BY client_host, user, db
ORDER BY conns DESC;

-- 2 长事务：持锁时间与回滚段大小都从这里判断
SELECT trx_id, trx_state, trx_started,
       TIMESTAMPDIFF(SECOND, trx_started, NOW()) AS running_seconds,
       trx_rows_locked, trx_rows_modified,
       LEFT(trx_query, 120) AS query_head
FROM information_schema.innodb_trx
WHERE trx_started < NOW() - INTERVAL 1 MINUTE
ORDER BY trx_started;

-- 3 锁等待：8.0 用 data_lock_waits，performance_schema 需开 wait/lock instrumentation
SELECT requesting_engine_thread_id, blocking_engine_thread_id
FROM sys.innodb_lock_waits
ORDER BY wait_age_seconds DESC LIMIT 20;

-- 4 全表扫描与未走索引的语句摘要
SELECT query, db, exec_count, no_index_used_count, rows_sent, rows_examined
FROM sys.statements_with_full_table_scans
WHERE db = DATABASE()
ORDER BY rows_examined DESC LIMIT 20;

-- 5 没用上的索引（写入放大与空间都白花）
SELECT object_schema, object_name, index_name
FROM sys.schema_unused_indexes
WHERE object_schema = DATABASE() LIMIT 50;

-- 6 重复索引与冗余索引：同前列前缀重复即命中
SELECT table_name, redundant_indexes, num_redundant_indexes
FROM (
    SELECT a.table_name,
           GROUP_CONCAT(CONCAT(a.index_name, '=', b.index_name) SEPARATOR ', ') AS redundant_indexes,
           count(*) AS num_redundant_indexes
    FROM information_schema.statistics a
    JOIN information_schema.statistics b
      ON a.table_schema = b.table_schema
     AND a.table_name = b.table_name
     AND a.index_name <> b.index_name
     AND a.column_name = b.column_name
     AND a.seq_in_index = 1
     AND b.seq_in_index = 1
    WHERE a.table_schema = DATABASE()
    GROUP BY a.table_name
) x
WHERE num_redundant_indexes > 0 LIMIT 20;

-- 7 体积与碎片：data_free 高说明删除后空间没回收
SELECT table_name,
       engine,
       table_rows,
       ROUND((data_length + index_length) / 1024 / 1024, 1)  AS size_mb,
       ROUND(data_free / 1024 / 1024, 1)                     AS free_mb
FROM information_schema.tables
WHERE table_schema = DATABASE() AND table_type = 'BASE TABLE'
ORDER BY (data_length + index_length) DESC LIMIT 20;

-- 8 缺主键的表（InnoDB 无主键会隐式加 6 字节_rowid，更新与复制都吃亏）
SELECT t.table_name
FROM information_schema.tables t
LEFT JOIN (SELECT DISTINCT table_schema, table_name
           FROM information_schema.table_constraints
           WHERE constraint_type = 'PRIMARY KEY') pk
       ON pk.table_schema = t.table_schema AND pk.table_name = t.table_name
WHERE t.table_schema = DATABASE() AND t.table_type = 'BASE TABLE' AND pk.table_name IS NULL;

-- 9 关键护栏参数是否被放宽
SHOW VARIABLES WHERE variable_name IN
    ('sql_mode', 'slow_query_log', 'long_query_time', 'innodb_lock_wait_timeout',
     'max_connections', 'wait_timeout', 'binlog_format', 'innodb_flush_log_at_trx_commit',
     'sync_binlog', 'character_set_server', 'collation_server', 'default_authentication_plugin');
