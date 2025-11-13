from time import strptime
from pydantic import BaseModel, Field
from typing_extensions import Optional

from app.core.config import settings

class RegisterIn(BaseModel):
    """ 用户名和密码前端加密后提交 """
    username: str
    password: str

class TokenWithRefresh(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    svr_pubkey: Optional[str] = Field(None, max_length=256, description="后端生成的SM2公钥，用于前端加密")

class UserOut(BaseModel):
    userid: str
    username: str

class LoginModel(RegisterIn):
    """登录请求模型"""
    phoneinfo: str = Field(max_length=256, description="设备信息")
    cli_pubkey: str = Field(max_length=256, description="前端生成传给后台用于加密的公钥")
