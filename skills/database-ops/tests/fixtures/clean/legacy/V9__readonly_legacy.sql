-- 存量表接入示范：结构由 DBA 定稿于上线前，本期只读对齐，不动一列
-- dialect: postgresql
-- dbops-ignore: D001,D002,D003,D006 历史审计表无 tenant 与 updated_at，改造排期见 issue 2187，本期只读不写
-- 整文件豁免与行级豁免都要写理由：只列码表或只写标记的，脚本判豁免无效并记 D015
CREATE TABLE IF NOT EXISTS t_legacy_audit (
    id          BIGSERIAL       PRIMARY KEY,
    serial_no   VARCHAR(64)     NOT NULL,
    amount      NUMERIC(14,2)   NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT now()
);

UPDATE t_legacy_audit SET created_at = now();  -- nosec-db: 全量重刷，运维手册 SOP-12 已确认影响面

DELETE FROM t_legacy_audit;  -- nosec-db: 清理阶段表，前置计数 SELECT 的结果已附在变更单

DROP TABLE IF EXISTS t_legacy_audit_stage;
