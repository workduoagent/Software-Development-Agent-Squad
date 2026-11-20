CREATE TABLE app_user (
    id BIGINT PRIMARY KEY,
    username VARCHAR(64) NOT NULL,
    password_hash VARCHAR(128) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by BIGINT,
    updated_by BIGINT,
    tenant VARCHAR(32) NOT NULL
);
CREATE INDEX idx_app_user_tenant ON app_user (tenant);
