-- 变更：example_biz 新增 settle_period 并回填存量行（PostgreSQL 版）
-- dialect: postgresql
-- 幂等：可重复执行；回填语句带 IS NULL 条件，重跑不覆盖已回填值
-- 档别：修改（动存量行），需变更单 + 备份 + 校验

-- 1 预查：把结果记进变更单，与预期不符先停下来
SELECT count(*) AS pending_rows FROM example_biz WHERE settle_period IS NULL;

-- 2 加可空列（先不加约束，避免长锁与存量行违规）
ALTER TABLE example_biz ADD COLUMN IF NOT EXISTS settle_period VARCHAR(7);
COMMENT ON COLUMN example_biz.settle_period IS '结算期 YYYY-MM，由 created_at 归集';

-- 3 分批回填：PG 无 UPDATE ... LIMIT，用主键子查询限定批次；每批之间确认锁等待与复制延迟
UPDATE example_biz SET settle_period = to_char(created_at, 'YYYY-MM')
WHERE id IN (
    SELECT id FROM example_biz
    WHERE settle_period IS NULL
    ORDER BY id
    LIMIT 2000
);
-- 重复执行第 3 步直到影响行数为 0

-- 4 补约束：先 NOT VALID 挡新脏数据，再全量校验，最后 VALIDATE
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_example_biz_settle_period') THEN
        ALTER TABLE example_biz
            ADD CONSTRAINT ck_example_biz_settle_period CHECK (settle_period ~ '^[0-9]{4}-(0[1-9]|1[0-2])$') NOT VALID;
    END IF;
END
$$;

ALTER TABLE example_biz VALIDATE CONSTRAINT ck_example_biz_settle_period;

-- 5 校验（期望：两行都是 0，输出留存为交付凭证）
SELECT count(*) AS still_null FROM example_biz WHERE settle_period IS NULL;
SELECT count(*) AS bad_format FROM example_biz
WHERE settle_period IS NOT NULL AND settle_period NOT SIMILAR TO '[0-9]{4}-(0[1-9]|1[0-2])';

-- 6 需要 NOT NULL 时单独开一个版本执行，不和回填挤在同一脚本里：
--    ALTER TABLE example_biz ALTER COLUMN settle_period SET NOT NULL;
