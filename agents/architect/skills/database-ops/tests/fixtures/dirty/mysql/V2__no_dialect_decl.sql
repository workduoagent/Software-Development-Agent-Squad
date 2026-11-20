-- 反例夹具：文件头漏写方言声明，脚本无法判定混用，只能记 WARN 让人去问
CREATE TABLE IF NOT EXISTS t_tag (
    id          BIGINT          NOT NULL,
    tenant      VARCHAR(32)     NOT NULL,
    name        VARCHAR(64)     NOT NULL,
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ     NOT NULL DEFAULT now(),
    created_by  VARCHAR(64)     NOT NULL DEFAULT '',
    updated_by  VARCHAR(64)     NOT NULL DEFAULT '',
    PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS idx_t_tag_tenant ON t_tag (tenant);
