from pydantic import BaseModel, Field
from typing import Generic, TypeVar, List, Optional

T = TypeVar("T")

class PageParams(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=200)
    # 允许 sort 形如: "-created_at,amount"
    sort: Optional[str] = Field(None, description="排序字段，逗号分隔，'-'前缀表示倒序")

class PageResult(BaseModel, Generic[T]):
    page: int
    page_size: int
    total: int
    items: List[T]