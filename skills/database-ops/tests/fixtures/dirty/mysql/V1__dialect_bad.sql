-- 反例夹具：声明 mysql 却写 PG 专有语法，索引键长超限，金额列无精度
-- dialect: mysql
-- 覆盖：D007 DATETIME 未声明口径、D008 无精度金额、D009 方言混入、D011 索引键长

CREATE TABLE IF NOT EXISTS t_user (
    id          BIGINT          NOT NULL,
    tenant      VARCHAR(32)     NOT NULL,
    email       VARCHAR(1000)   NOT NULL,
    amount      DECIMAL,
    created_at  DATETIME(3),
    updated_at  DATETIME(3),
    created_by  VARCHAR(64),
    updated_by  VARCHAR(64),
    PRIMARY KEY (id),
    UNIQUE KEY uk_t_user_tenant_email (tenant, email),
    KEY idx_t_user_tenant (tenant)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

INSERT INTO t_user (id, tenant) VALUES (1, 'a') ON CONFLICT (id) DO NOTHING;

SELECT id FROM t_user WHERE email ILIKE '%@corp%' RETURNING id;

ALTER TABLE t_user ADD COLUMN meta JSONB;
