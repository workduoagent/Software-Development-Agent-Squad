-- 反例夹具：豁免只列码表不写理由，D015 拦下且豁免不生效，被豁免的规则照常命中
-- dialect: postgresql
-- dbops-ignore: D001,D002,D006
CREATE TABLE IF NOT EXISTS t_legacy_bad (
    id          BIGSERIAL       PRIMARY KEY,
    serial_no   VARCHAR(64)     NOT NULL,
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT now()
);

UPDATE t_legacy_bad SET serial_no = serial_no;  -- nosec-db:
