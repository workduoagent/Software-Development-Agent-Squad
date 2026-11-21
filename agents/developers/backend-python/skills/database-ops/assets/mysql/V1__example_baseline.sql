-- 表：example_biz（示例业务表，MySQL 8 落地板）
-- dialect: mysql
-- 时区口径：DATETIME(3) 无时区，服务端与连接统一 connectionTimeZone=+08:00，应用侧不做二次换算
-- 幂等：建表与索引内联在 CREATE TABLE IF NOT EXISTS 内，可重复执行；后续补索引无 IF NOT EXISTS，重跑报 1061，由 Flyway 版本表保证只执行一次

CREATE TABLE IF NOT EXISTS `example_biz` (
    `id`          BIGINT        NOT NULL COMMENT '雪花 ID，应用侧生成，对外序列化为字符串',
    `created_at`  DATETIME(3)   NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '创建时间',
    `updated_at`  DATETIME(3)   NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3) COMMENT '更新时间',
    `created_by`  BIGINT        NULL COMMENT '创建人，系统任务为 NULL',
    `updated_by`  BIGINT        NULL COMMENT '更新人',
    `tenant`      BIGINT        NOT NULL DEFAULT 0 COMMENT '租户 ID，0 为系统保留租户',
    `name`        VARCHAR(128)  NOT NULL COMMENT '名称，租户内唯一',
    `status`      SMALLINT      NOT NULL DEFAULT 0 COMMENT '状态：0 草稿 1 生效 2 停用',
    `amount`      DECIMAL(14,2) NULL COMMENT '金额，单位元，两位小数，禁止浮点',
    `extra`       JSON          NULL COMMENT '扩展属性，仅限非契约字段；查询需要时改生成列',
    `remark`      VARCHAR(512)  NULL COMMENT '备注',
    PRIMARY KEY (`id`),
    KEY `idx_example_biz_tenant` (`tenant`),
    KEY `idx_example_biz_tenant_status_created` (`tenant`, `status`, `created_at` DESC),
    UNIQUE KEY `uk_example_biz_tenant_name` (`tenant`, `name`),
    CONSTRAINT `ck_example_biz_status` CHECK (`status` IN (0, 1, 2))
) ENGINE = InnoDB
  ROW_FORMAT = DYNAMIC
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_0900_ai_ci COMMENT '示例业务表';

-- 与 PostgreSQL 版的三处实质差异，移植时逐条核对：
--   1. 排序规则 ai_ci 大小写不敏感，(tenant, name) 唯一约束会把 Abc 与 abc 判为同一个；
--      需要大小写敏感时改用 utf8mb4_0900_as_cs 或把该列纳入生成列后建索引。
--   2. created_at DESC 是 8.0 才支持的降序索引，5.7 会静默忽略，索引顺序断言不能跨版本照搬。
--   3. CHECK 约束 8.0.16 起才真正强制，更早版本形同注释。
--
-- 回滚：DDL 隐式提交，失败即半套落地，不能靠事务撤销。执行前必须先备份：
--   mysqldump --no-data app_db example_biz > /backup/example_biz_schema_$(date +%F).sql
--   恢复命令：SOURCE /backup/example_biz_schema_YYYY-MM-DD.sql（或 mysql app_db < 同名文件）
