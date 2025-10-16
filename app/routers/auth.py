from datetime import datetime, timezone
import json
import logging
import uuid

from fastapi import APIRouter, Depends, Form, HTTPException, Response, status
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_limiter.depends import RateLimiter
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user
from app.core.exceptions import BizException
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    validate_password_strength,
    verify_password,
)
from app.core.session_store import (
    clear_user_session,
    get_user_session,
    get_user_session_data,
    new_session_id,
    set_user_session,
    set_user_session_data,
)
from app.db.models import Logger, User
from app.db.session import get_db
from app.schemas.auth import RegisterIn, TokenWithRefresh, UserOut, loginModel
from app.schemas.response import R

router = APIRouter()

@router.post("/register", response_model=R[None], dependencies=[Depends(RateLimiter(times=5, seconds=60))])
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    exists = db.query(User).filter(User.username == payload.username).first()
    if exists:
        raise BizException(message="用户名已存在")
    # 验证密码复杂度
    validate_password_strength(payload.password)
    user = User(username=payload.username, password_hash=hash_password(payload.password))
    db.add(user); db.commit()
    return R.ok(message="注册成功")


@router.post("/login", response_model=R[TokenWithRefresh], dependencies=[Depends(RateLimiter(times=5, seconds=60))])
async def login(request: Request, payload: loginModel, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise BizException(message="用户名或密码错误")

    sid = await new_session_id()
    await set_user_session(user.userid, sid)
    
    # 创建访问令牌和刷新令牌
    access_token = create_access_token({"sub": user.userid, "sid": sid})
    refresh_token = create_refresh_token({"sub": user.userid, "sid": sid})

    # 将刷新令牌存储到Redis，用于验证和注销
    await set_user_session_data(user.userid, "refresh_token", refresh_token)

    # 增强日志记录，添加更多上下文信息
    log_info = {
        "phone_info": payload.phoneinfo,
        "ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("User-Agent", ""),
        "login_time": datetime.now(timezone.utc).isoformat()
    }
    logger = Logger(userid=user.userid, action="login", info=json.dumps(log_info, ensure_ascii=False))
    db.add(logger); db.commit()
    
    # 同时记录到应用日志
    logging.getLogger("auth").info(
        "User logged in",
        extra={
            "user_id": user.userid,
            "username": user.username,
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("User-Agent", ""),
            "phone_info": payload.phoneinfo
        }
    )

    # 直接返回响应数据，让FastAPI自动处理响应创建
    # 这样可以确保CORS头等必要的头信息被正确设置
    return R.ok(data={
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    })

@router.post("/refresh", response_model=R[TokenWithRefresh], dependencies=[Depends(RateLimiter(times=5, seconds=60))])
async def refresh_token(
    refresh_token: str = Form(),
    db: Session = Depends(get_db)
):
    """使用刷新令牌获取新的访问令牌和刷新令牌"""
    try:
        # 解码刷新令牌
        payload = decode_token(refresh_token)
        
        # 验证令牌类型
        if payload.get("type") != "refresh":
            raise BizException(message="无效的刷新令牌类型")
        
        user_id = payload.get("sub")
        sid = payload.get("sid")
        
        if not user_id or not sid:
            raise BizException(message="无效的刷新令牌")
        
        # 验证用户是否存在
        user = db.query(User).filter(User.userid == user_id).first()
        if not user:
            raise BizException(message="用户不存在")
        
        # 验证会话ID是否有效
        current_sid = await get_user_session(user_id)
        if current_sid is None or current_sid != sid:
            raise BizException(message="该账号已在其他设备登录")
        
        # 验证存储的刷新令牌是否匹配（防止令牌重用）
        stored_refresh_token = await get_user_session_data(user_id, "refresh_token")
        if stored_refresh_token != refresh_token:
            raise BizException(message="无效的刷新令牌")
        
        # 生成新的访问令牌和刷新令牌
        new_access_token = create_access_token({"sub": user_id, "sid": sid})
        new_refresh_token = create_refresh_token({"sub": user_id, "sid": sid})
        
        # 更新存储的刷新令牌
        await set_user_session_data(user_id, "refresh_token", new_refresh_token)
        
        # 创建FastAPI Response对象
        return JSONResponse(
            content=R.ok(data={
                "access_token": new_access_token,
                "refresh_token": new_refresh_token,
                "token_type": "bearer",
                "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            }).model_dump(),
            headers={
                "Cache-Control": "no-store",
                "Pragma": "no-cache"
            }
        )
        
    except BizException as e:
        raise e
    except Exception:
        raise BizException(message="令牌刷新失败")


@router.get("/me", response_model=R[UserOut])
async def me(current_user: User = Depends(get_current_user)):
    return R.ok(data={"userid": current_user.userid, "username": current_user.username})


@router.post("/logout", response_model=R[None])
async def logout(current_user: User = Depends(get_current_user)):
    await clear_user_session(current_user.userid)
    return R.ok(message="退出成功")