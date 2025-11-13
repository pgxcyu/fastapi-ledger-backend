from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field
from pydantic.config import ConfigDict

from app.domains.enums import TransactionType
from app.schemas.basic import PageParams

class FileInfo(BaseModel):
    filepath: str
    fileid: Optional[str] = None
    photo_id: Optional[str] = None


class TransactionCreate(BaseModel):
    amount: float = Field(default=0, gt=0, description="交易金额必须大于0")
    type: TransactionType = Field(default=TransactionType.INCOME, description="交易类型必须是枚举值")
    remark: Optional[str] = Field(default="", max_length=255, description="交易备注最大长度为255")
    filelist: Optional[List[FileInfo]] = Field(default_factory=[], description="交易文件列表")
    # 以下为修改用字段
    transaction_id: Optional[str] = Field(None, description="交易ID，全局唯一")
    delFileids: Optional[str] = Field(None, description="要删除的文件ID拼接，多个ID用英文逗号分隔")


class TransactionResponse(BaseModel):
    transaction_id: str
    create_userid: str
    create_username: Optional[str] = None
    update_userid: Optional[str] = None
    update_username: Optional[str] = None
    amount: float
    type: TransactionType
    remark: Optional[str] = None
    filelist: Optional[List[FileInfo]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class TransactionListQuery(PageParams):
    date_from: Optional[datetime] = Field(None, description="开始时间（含）")
    date_to: Optional[datetime] = Field(None, description="结束时间（含）")
    type: Optional[TransactionType] = None
    min_amount: Optional[float] = Field(None, ge=0)
    max_amount: Optional[float] = Field(None, ge=0)
    keyword: Optional[str] = Field(None, description="搜索备注/类型（模糊查询）")
    userid: Optional[str] = Field(None, description="用户ID")