-- PostgreSQL 16 体检：只读账号即可执行，逐项对应 references/operations.md 第二、三、五节
-- dialect: postgresql
-- 用法：psql "$DSN" -f pg_health_check.sql -P pager=off ；输出贴进排障记录或交付凭证

-- 1 连接水位：总数与按状态分布，接近 max_connections 即告警
SHOW max_connections;
SELECT count(*) AS total,
       count(*) FILTER (WHERE state = 'active')              AS active,
       count(*) FILTER (WHERE state = 'idle')                AS idle,
       count(*) FILTER (WHERE state = 'idle in transaction') AS idle_in_tx
FROM pg_stat_activity
WHERE backend_type = 'client backend';

-- 2 谁占着连接：按应用名统计（依赖 datasource-postgres.yml 里的 ApplicationName）
SELECT application_name, usename, datname, count(*) AS conns
FROM pg_stat_activity
WHERE backend_type = 'client backend'
GROUP BY 1, 2, 3
ORDER BY conns DESC;

-- 3 长事务与空闲事务：空闲事务会挡住 vacuum 与 DDL，超阈值必须处理
SELECT pid, usename, application_name, state,
       now() - xact_start  AS xact_age,
       now() - query_start AS query_age,
       left(query, 120)    AS query_head
FROM pg_stat_activity
WHERE backend_type = 'client backend'
  AND state <> 'idle'
  AND now() - xact_start > interval '1 minute'
ORDER BY xact_start;

-- 4 锁等待链：被谁挡住，挡住的语句是什么
SELECT w.pid AS waiting_pid, left(w.query, 80) AS waiting_query,
       b.pid AS blocking_pid, left(b.query, 80) AS blocking_query
FROM pg_stat_activity w
JOIN LATERAL unnest(pg_blocking_pids(w.pid)) AS blk(pid) ON true
JOIN pg_stat_activity b ON b.pid = blk.pid
WHERE cardinality(pg_blocking_pids(w.pid)) > 0;

-- 5 缓存命中与顺序扫描占比：定位"表变大后突然变慢"
SELECT relname,
       seq_scan, idx_scan,
       round(seq_scan::numeric / nullif(seq_scan + idx_scan, 0) * 100, 1) AS seq_scan_pct,
       n_live_tup, n_dead_tup, last_autovacuum, last_autoanalyze
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC
LIMIT 20;

SELECT round(blks_hit::numeric / nullif(blks_hit + blks_read, 0) * 100, 2) AS cache_hit_pct
FROM pg_stat_database WHERE datname = current_database();

-- 6 膨胀与体积：dead tuples 高且 autovacuum 没跑过就要人工介入
SELECT c.relname,
       pg_size_pretty(pg_total_relation_size(c.oid)) AS total_size,
       pg_size_pretty(pg_relation_size(c.oid))       AS heap_size,
       s.n_dead_tup
FROM pg_class c
JOIN pg_stat_user_tables s ON s.relid = c.oid
WHERE c.relkind = 'r'
ORDER BY pg_total_relation_size(c.oid) DESC
LIMIT 20;

-- 7 没用上的索引与建失败的索引：CONCURRENTLY 中断会留下 INVALID，必须删掉重建
SELECT schemaname, relname, indexrelname, idx_scan
FROM pg_stat_user_indexes
WHERE idx_scan = 0 AND schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY pg_relation_size(indexrelid) DESC
LIMIT 20;

SELECT c.relname AS table_name, i.relname AS index_name
FROM pg_index x
JOIN pg_class i ON i.oid = x.indexrelid
JOIN pg_class c ON c.oid = x.indrelid
WHERE NOT x.indisvalid;

-- 8 缺主键的表：无主键表的更新与逻辑复制都是隐患
SELECT c.relname
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind = 'r'
  AND n.nspname = current_schema()
  AND NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = c.oid AND contype = 'p');

-- 9 统计信息新鲜度：估算与实际差一个数量级先 ANALYZE
SELECT relname, last_analyze, last_autoanalyze
FROM pg_stat_user_tables
WHERE last_analyze IS NULL AND last_autoanalyze IS NULL
ORDER BY relname;
