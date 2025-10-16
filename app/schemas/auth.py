from pydantic import BaseModel, Field
from app.core.config import settings

class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=6, max_length=128)

class TokenWithRefresh(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

class UserOut(BaseModel):
    userid: str
    username: str

class loginModel(RegisterIn):
    """登录请求模型"""
    phoneinfo: str = Field(max_length=256, description="设备信息")