from pydantic import BaseModel, Field
from pydantic.config import ConfigDict
from typing_extensions import Optional, List

from app.core.config import settings

class RoleOut(BaseModel):
    role_id: str
    role_name: str
    role_code: str

    model_config = ConfigDict(from_attributes=True)

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
    idcard: Optional[str] = Field(None, max_length=18, description="用户身份证号")
    phone: Optional[str] = Field(None, max_length=12, description="用户手机号")
    name: Optional[str] = Field(None, max_length=12, description="用户姓名")
    roles: Optional[List[RoleOut]] = Field(None, description="用户角色列表")
    role_id: Optional[str] = Field(None, description="用户当前角色ID")
    role_name: Optional[str] = Field(None, description="用户当前角色名称")
    role_code: Optional[str] = Field(None, description="用户当前角色代码")


class LoginModel(RegisterIn):
    """登录请求模型"""
    phoneinfo: str = Field(max_length=256, description="设备信息")
    cli_pubkey: str = Field(max_length=256, description="前端生成传给后台用于加密的公钥")

class SwitchRoleIn(BaseModel):
    role_id: str