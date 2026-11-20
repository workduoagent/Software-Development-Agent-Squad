-- 反例夹具：一文件踩多条规则，期望退出码 1
-- dialect: postgresql
-- 覆盖 ERROR 级 D001 D002 D003 D004 D005 D006 D008 D009
-- 覆盖 WARN  级 D007 D012 D014

CREATE TABLE t_order (
    id          BIGSERIAL       PRIMARY KEY,
    order_no    VARCHAR(64),
    tenant      VARCHAR(32),
    amount      DOUBLE PRECISION,
    status      TIMESTAMP,
    created_at  TIMESTAMP
);

CREATE UNIQUE INDEX uk_t_order_no ON t_order (order_no);

INSERT INTO t_order (order_no, amount) VALUES ('A-1', 1.5) ON DUPLICATE KEY UPDATE amount = 1.5;

UPDATE t_order SET status = now();

DELETE FROM t_order;

ALTER TABLE t_order ADD COLUMN channel VARCHAR(32) NOT NULL;

TRUNCATE t_order_history;

SELECT * FROM t_order;
