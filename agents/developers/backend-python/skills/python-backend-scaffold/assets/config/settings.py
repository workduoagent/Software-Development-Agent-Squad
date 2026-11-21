"""应用配置：全部取值来自环境变量（前缀 SQUAD_）；缺失密钥 fail-fast，不给默认值。

设备环境事实（本机地址、实例归属）的取值真源是本机仓库根 device-env.md；口令只记环境变量名，不入本文件。
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SQUAD_", extra="ignore")

    app_name: str
    # 例：postgresql+psycopg://squad_app:${SQUAD_PG_PASSWORD}@127.0.0.1:5432/squad_dev
    database_url: str
    jwt_secret: str

    # 待拍板参数：取值以 Tech Spec §七 为准，不得自行假定（基线第九节留白项）
    jwt_expire_minutes: int = 120
    audit_retention_days: int = 180
