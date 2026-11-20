-- 表：t_order 订单主表，与 postgresql/ 同模型，用于校验 MySQL 8 方言分支
-- dialect: mysql
-- 幂等：MySQL 8 没有 CREATE INDEX IF NOT EXISTS，索引一律写在建表块内
-- 时区口径：库、连接、JVM 三处统一 UTC，DATETIME 不做隐式转换
-- 用途：check_db_ops.sh 的干净夹具，期望退出码 0

CREATE TABLE IF NOT EXISTS t_order (
    id              BIGINT          NOT NULL,
    tenant          VARCHAR(32)     NOT NULL,
    order_no        VARCHAR(64)     NOT NULL,
    amount          DECIMAL(14,2)   NOT NULL DEFAULT 0,
    status          TINYINT         NOT NULL DEFAULT 0,
    remark          VARCHAR(512)    NOT NULL DEFAULT '',
    extra           JSON,
    created_at      DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    updated_at      DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
    created_by      VARCHAR(64)     NOT NULL DEFAULT '',
    updated_by      VARCHAR(64)     NOT NULL DEFAULT '',
    PRIMARY KEY (id),
    UNIQUE KEY uk_t_order_tenant_no (tenant, order_no),
    KEY idx_t_order_tenant_status (tenant, status, created_at),
    CONSTRAINT ck_t_order_amount CHECK (amount >= 0)
) ENGINE = InnoDB ROW_FORMAT = DYNAMIC DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci;
