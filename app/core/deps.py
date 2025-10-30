from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import BizException
from app.core.session_store import get_active_sid
from app.db.models import User
from app.db.session import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exc = BizException(code=401, message="无效的token")

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        sub = payload.get("sub")
        sid = payload.get("sid")
        if sub is None or sid is None:
            raise credentials_exc
    except JWTError:
        raise credentials_exc

    current_sid = await get_active_sid(sub)
    if current_sid is None or current_sid != sid:
        raise BizException(code=401, message="该账号已在其他设备登录")

    user = db.query(User).filter(User.userid == sub).first()
    if not user:
        raise BizException(code=500, message="用户不存在")
    
    setattr(user, "sid", sid)
    return user
