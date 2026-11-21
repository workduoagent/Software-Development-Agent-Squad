-- 表：example_biz（示例业务表，作为新表设计的最小骨架）
-- dialect: postgresql
-- 幂等：可重复执行，全部语句带 IF NOT EXISTS；约束用 DO 块补齐同语义
-- 说明：迁移到 src/main/resources/db/migration/postgresql/V{n}__{描述}.sql，版本号严格递增

CREATE TABLE IF NOT EXISTS example_biz (
    id          BIGINT       PRIMARY KEY,
    -- 六大基石（与 BaseEntity 字段一一对应，列名统一 created_at / updated_at）
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    created_by  BIGINT,
    updated_by  BIGINT,
    tenant      BIGINT       NOT NULL DEFAULT 0,
    -- 业务字段
    name        VARCHAR(128) NOT NULL,
    status      SMALLINT     NOT NULL DEFAULT 0,
    amount      NUMERIC(14,2),
    extra       JSONB,
    remark      VARCHAR(512)
);

COMMENT ON TABLE  example_biz            IS '示例业务表';
COMMENT ON COLUMN example_biz.id         IS '雪花 ID，应用侧生成，对外序列化为字符串';
COMMENT ON COLUMN example_biz.tenant     IS '租户 ID，0 为系统保留租户';
COMMENT ON COLUMN example_biz.status     IS '状态：0 草稿 1 生效 2 停用';
COMMENT ON COLUMN example_biz.amount     IS '金额，单位元，两位小数，禁止浮点';
COMMENT ON COLUMN example_biz.extra      IS '扩展属性，仅限非契约字段；稳定字段必须提升为列';

-- tenant 前导索引：强制项，租户隔离查询的主入口（门禁 D003）
CREATE INDEX IF NOT EXISTS idx_example_biz_tenant ON example_biz (tenant);
-- 复合索引按"等值在前、排序在后"，服务列表页 WHERE tenant = ? AND status = ? ORDER BY created_at DESC
CREATE INDEX IF NOT EXISTS idx_example_biz_tenant_status_created
    ON example_biz (tenant, status, created_at DESC);
-- 业务唯一性必须带租户维度，裸业务键会挡住跨租户同名
CREATE UNIQUE INDEX IF NOT EXISTS uk_example_biz_tenant_name ON example_biz (tenant, name);

-- PG 的 ADD CONSTRAINT 没有 IF NOT EXISTS，幂等靠目录表判断，不要直接裸写
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_example_biz_status') THEN
        ALTER TABLE example_biz ADD CONSTRAINT ck_example_biz_status CHECK (status IN (0, 1, 2));
    END IF;
END
$$;

-- 可选列，仅在契约里有对应语义时才加，加了就承担对应义务：
--   is_deleted SMALLINT NOT NULL DEFAULT 0   软删除，所有查询必须带条件，唯一索引需纳入该列或用部分索引
--   version    INTEGER  NOT NULL DEFAULT 0   乐观锁，必须配 MyBatis-Plus @Version，否则是死列

-- 回滚：社区版 Flyway 不自动执行 undo。可逆变更另开 U{n}__xxx.sql；
-- 删列删表属破坏性变更，执行前先做结构备份并在回滚脚本里写明恢复命令。
