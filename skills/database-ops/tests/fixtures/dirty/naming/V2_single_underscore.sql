-- 反例夹具：版本号与描述之间只有一个下划线，Flyway 会把整个文件名当版本号解析
-- dialect: postgresql
CREATE TABLE IF NOT EXISTS t_pay (
    id BIGINT PRIMARY KEY, tenant VARCHAR(32) NOT NULL, amount NUMERIC(14,2) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by VARCHAR(64) NOT NULL DEFAULT '', updated_by VARCHAR(64) NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_t_pay_tenant ON t_pay (tenant);
