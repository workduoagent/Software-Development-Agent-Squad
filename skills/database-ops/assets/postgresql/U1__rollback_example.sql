-- 回滚：撤销 V3__add_settle_period（PostgreSQL 版，社区版 Flyway 不自动执行 undo，人工按序跑）
-- dialect: postgresql
-- 档别：破坏性（删列），执行前必须完成备份并确认恢复路径
-- 备份（结构 + 数据，产物路径记进变更单）：
--   pg_dump -t example_biz -Fc app_db > /backup/example_biz_$(date +%F).dump
-- 恢复命令（回滚失败时的兜底，恢复耗时约等于 dump 体积除以restore并行度）：
--   pg_restore -d app_db --single-transaction /backup/example_biz_YYYY-MM-DD.dump

-- 1 先确认这一列没有被在线代码引用：应用侧全仓搜 settle_period，零引用才继续
-- 2 删列前先摘掉依赖它的约束与索引，顺序不能反
DROP INDEX IF EXISTS idx_example_biz_tenant_settle_period;
ALTER TABLE example_biz DROP CONSTRAINT IF EXISTS ck_example_biz_settle_period;
ALTER TABLE example_biz DROP COLUMN IF EXISTS settle_period;

-- 3 校验：列已不存在，期望返回 0 行
SELECT count(*) AS still_present
FROM information_schema.columns
WHERE table_name = 'example_biz' AND column_name = 'settle_period';

-- 说明：PG 的 DDL 在事务里可回滚，生产执行建议包一层 BEGIN / COMMIT，
-- 校验不通过就 ROLLBACK，而不是边试边改。
