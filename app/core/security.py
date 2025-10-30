from datetime import datetime, timedelta, timezone
import re

from fastapi import Depends
from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.crypto_sm2 import make_sm2
from app.core.deps import get_current_user
from app.core.exceptions import BizException
from app.core.session_store import get_active_sid, get_session_kv
from app.db.models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 密码复杂度要求：至少8位，包含大小写字母、数字和特殊字符
def validate_password_strength(password: str) -> None:
    """验证密码复杂度"""
    if len(password) < 8:
        raise BizException(message="密码长度至少为8位")
    if not re.search(r"[A-Z]", password):
        raise BizException(message="密码必须包含至少一个大写字母")
    if not re.search(r"[a-z]", password):
        raise BizException(message="密码必须包含至少一个小写字母")
    if not re.search(r"[0-9]", password):
        raise BizException(message="密码必须包含至少一个数字")
    if not re.search(r"[^A-Za-z0-9]", password):
        raise BizException(message="密码必须包含至少一个特殊字符")

def hash_password(pw: str) -> str:
    return pwd_context.hash(pw)

def verify_password(pw: str, hashed: str) -> bool:
    return pwd_context.verify(pw, hashed)

def create_access_token(data: dict, minutes: int = settings.ACCESS_TOKEN_EXPIRE_MINUTES):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def create_refresh_token(data: dict, days: int = settings.REFRESH_TOKEN_EXPIRE_DAYS):
    """创建刷新令牌，有效期通常比访问令牌长"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=days)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_token(token: str) -> dict:
    """解码JWT令牌并返回其内容"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except jwt.JWTError:
        raise BizException(code=401, message="无效的令牌")



# 创建SM2客户端，用于会话期间加密/解密
async def get_sm2_client(current_user: User = Depends(get_current_user)):
    # 优先使用 current_user 上可能已经设置的 sid
    sid = getattr(current_user, "sid", None)
    if not sid:
        # 如果没有，再从活动会话中获取
        sid = await get_active_sid(current_user.userid)
        if not sid:
            raise BizException(code=401, message="未登录或登录过期")
    
    cli_pubkey = await get_session_kv(sid, "cli_pubkey")
    svr_privkey = await get_session_kv(sid, "svr_privkey")

    if not cli_pubkey or not svr_privkey:
        raise BizException(message="获取SM2密钥对失败")
    return make_sm2(svr_privkey, cli_pubkey, strict=False)
