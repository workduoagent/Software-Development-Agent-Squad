-- 变更：example_biz 新增 settle_period 并回填存量行（MySQL 8 版）
-- dialect: mysql
-- 时区口径：created_at 为 DATETIME(3)，会话时区固定 +08:00，DATE_FORMAT 直接取业务时间
-- 幂等：加列与建索引没有 IF NOT EXISTS，重复执行报 1061/1060；由 Flyway 版本表保证只执行一次，重跑前先查 information_schema
-- 档别：修改（动存量行），需变更单 + 备份 + 校验

-- 1 预查：把结果记进变更单
SELECT count(*) AS pending_rows FROM example_biz WHERE settle_period IS NULL;

-- 2 加可空列，INSTANT 算法避免全表重建；不支持时 MySQL 直接报错而不是悄悄锁表
ALTER TABLE example_biz
    ADD COLUMN settle_period VARCHAR(7) NULL COMMENT '结算期 YYYY-MM，由 created_at 归集',
    ALGORITHM = INSTANT;

-- 3 分批回填：单表更新可用 ORDER BY + LIMIT，必须按主键顺序，避免间隙锁范围扩大
UPDATE example_biz
SET settle_period = DATE_FORMAT(created_at, '%Y-%m')
WHERE settle_period IS NULL
ORDER BY id
LIMIT 2000;
-- 重复执行第 3 步直到影响行数为 0；批间观察 innodb_lock_wait 与复制延迟

-- 4 补索引与约束（分开执行，一条 DDL 一个版本，失败不会连坐）
ALTER TABLE example_biz
    ADD INDEX idx_example_biz_tenant_settle_period (tenant, settle_period),
    ALGORITHM = INPLACE, LOCK = NONE;

ALTER TABLE example_biz
    ADD CONSTRAINT ck_example_biz_settle_period CHECK (settle_period REGEXP '^[0-9]{4}-(0[1-9]|1[0-2])$');

-- 5 校验（期望：均为 0，输出留存为交付凭证）
SELECT count(*) AS still_null FROM example_biz WHERE settle_period IS NULL;
SELECT count(*) AS bad_format FROM example_biz
WHERE settle_period IS NOT NULL AND settle_period NOT REGEXP '^[0-9]{4}-(0[1-9]|1[0-2])$';

-- 6 需要 NOT NULL 时单独开一个版本：
--    ALTER TABLE example_biz MODIFY settle_period VARCHAR(7) NOT NULL COMMENT '结算期 YYYY-MM';
--    注意 MySQL 的 DDL 隐式提交，这一步失败不会自动回到上一步，必须先有结构备份。
