-- 表：t_order 订单主表，一行一笔订单，金额与状态都在这一张表上
-- dialect: postgresql
-- 幂等：建表与建索引全部带 IF NOT EXISTS，迁移中断后同版本重跑不报错
-- 用途：check_db_ops.sh 的干净夹具，期望退出码 0

CREATE TABLE IF NOT EXISTS t_order (
    id              BIGINT          NOT NULL,
    tenant          VARCHAR(32)     NOT NULL,
    order_no        VARCHAR(64)     NOT NULL,
    amount          NUMERIC(14,2)   NOT NULL DEFAULT 0,
    status          SMALLINT        NOT NULL DEFAULT 0,
    remark          VARCHAR(512)    NOT NULL DEFAULT '',
    extra           JSONB,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
    created_by      VARCHAR(64)     NOT NULL DEFAULT '',
    updated_by      VARCHAR(64)     NOT NULL DEFAULT '',
    CONSTRAINT pk_t_order_id PRIMARY KEY (id),
    CONSTRAINT uk_t_order_tenant_no UNIQUE (tenant, order_no),
    CONSTRAINT ck_t_order_amount CHECK (amount >= 0)
);

COMMENT ON TABLE t_order IS '订单主表';

CREATE INDEX IF NOT EXISTS idx_t_order_tenant_status
    ON t_order (tenant, status, created_at DESC);
