"""六大基石基类：迁移、模型、填充三处必须一致；tenant 必须是某索引的前导列（database-ops D002/D003）。"""
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """雪花 ID 应用侧生成（禁自增）；对外出参一律序列化为字符串（逐字段，禁全局转换）。"""

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    created_by: Mapped[str] = mapped_column(String(64))
    updated_by: Mapped[str] = mapped_column(String(64))
    tenant: Mapped[str] = mapped_column(String(64))


def tenant_index(table_name: str, *extra_columns: str) -> Index:
    """tenant 前导列复合索引工厂；每个业务表在模型上显式声明一份。"""
    tail = "_".join(extra_columns) if extra_columns else "id"
    columns = ("tenant", *(extra_columns or ("id",)))
    return Index(f"ix_{table_name}_tenant_{tail}", *columns)
