from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.crypto_sm2 import make_sm2
from app.core.exceptions import BizException
from app.core.request_ctx import set_user_context
from app.core.security import decode_token
from app.core.session_store import get_active_sid, get_session_kv
from app.db.db_session import get_db
from app.db.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

async def get_current_user(request: Request, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    payload = decode_token(token)
    sub = payload.get("sub")
    sid = payload.get("sid")
    if sub is None or sid is None:
        raise BizException(code=401, message="无效的token")

    current_sid = await get_active_sid(sub)
    if current_sid is None or current_sid != sid:
        raise BizException(code=401, message="该账号已在其他设备登录")

    user = db.query(User).filter(User.userid == sub).first()
    if not user:
        raise BizException(code=500, message="用户不存在")
    
    setattr(user, "sid", sid)
    return user


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
