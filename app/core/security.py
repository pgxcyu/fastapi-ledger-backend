from datetime import datetime, timedelta, timezone
import re
from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings
from app.core.exceptions import BizException

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
