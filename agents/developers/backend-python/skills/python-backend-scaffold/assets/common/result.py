"""统一响应包装与业务异常。

Result 三键固定（code/msg/data，成功码 200）；错误码规则 HTTP 状态 × 100 + 两位序号，
与 Java 侧共用契约 x-error-codes 同一张登记表，禁止孤儿码。
"""
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Result(BaseModel, Generic[T]):
    code: int = 200
    msg: str = "ok"
    data: T | None = None


class BusinessException(Exception):
    """service 层每条契约错误码对应一个抛出点；由 main.py 全局异常处理器统一转 Result。"""

    def __init__(self, code: int, msg: str) -> None:
        self.code = code
        self.msg = msg
        super().__init__(msg)
