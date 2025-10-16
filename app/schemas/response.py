# app/schemas/response.py
from typing import Generic, Optional, TypeVar
from pydantic import BaseModel

T = TypeVar("T")

class R(BaseModel, Generic[T]):
    code: int = 200
    message: str = "success"
    data: Optional[T] = None

    @staticmethod
    def ok(data: Optional[T] = None, message: str = "success") -> "R[T]":
        return R(code= 200, message=message, data=data)

    @staticmethod
    def fail(code: int = 500, message: str = "error", data: Optional[dict] = None) -> "R":
        return R(code=code, message=message, data=data)
