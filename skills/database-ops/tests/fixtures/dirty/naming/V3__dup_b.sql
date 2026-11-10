-- 反例夹具：同目录两个 V3，Flyway 启动即报版本冲突
-- dialect: postgresql
CREATE TABLE IF NOT EXISTS t_dup_b (
    id BIGINT PRIMARY KEY, tenant VARCHAR(32) NOT NULL, amount NUMERIC(14,2) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by VARCHAR(64) NOT NULL DEFAULT '', updated_by VARCHAR(64) NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_t_dup_b_tenant ON t_dup_b (tenant);
