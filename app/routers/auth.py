from datetime import datetime, timezone
import json

from fastapi import APIRouter, Body, Depends, Form
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi_limiter.depends import RateLimiter
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.crypto_sm2 import (
    gen_sm2_keypair,
    make_sm2,
    sm2_decrypt_hex,
    sm2_encrypt_hex,
)
from app.core.deps import get_current_user, get_sm2_client
from app.core.exceptions import BizException
from app.core.logging import auth_logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    validate_password_strength,
    verify_password,
)
from app.core.session_store import (
    add_user_session,
    clear_active_sid,
    delete_session_sid,
    expire_session_sid,
    get_active_sid,
    get_session_kv,
    new_session_id,
    set_active_sid,
    set_session_kv,
)
from app.db.db_session import get_db
from app.db.models import Resource, Role, RoleAreaGrant, User, UserRoleScope
from app.domains.enums import ResourceType, UserStatus
from app.schemas.auth import LoginModel, RegisterIn, RoleOut, TokenWithRefresh, UserOut, SwitchRoleIn
from app.schemas.response import R
from app.core.audit import audit_login

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
async def login(request: Request, payload: LoginModel, db: Session = Depends(get_db)):
    sm2_no_login = make_sm2(settings.SM2_PRIVATE_KEY_NOLOGIN, settings.SM2_PUBLIC_KEY_NOLOGIN)
    # username = sm2_no_login.decrypt(bytes.fromhex(payload.username)).decode("utf-8")
    username = sm2_decrypt_hex(sm2_no_login, payload.username)
    password = sm2_decrypt_hex(sm2_no_login, payload.password)

    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        raise BizException(message="用户名或密码错误")

    # 检查用户是否启用
    if user.status == UserStatus.DISABLED: raise BizException(message="用户已被禁用")
    if user.status == UserStatus.DELETED: raise BizException(message="用户已被删除")
    if user.status == UserStatus.PENDING: raise BizException(message="用户审核中")
    if user.status == UserStatus.FROZEN: raise BizException(message="用户已被冻结")

    # 检查用户是否有有效角色
    valid_roles = user.roles
    if not valid_roles:
        raise BizException(message="当前用户未配置有效角色")

    default_role = next((role for role in user.roles if role.role_id == user.default_role_id), None)
    cur_role_id = default_role.role_id if default_role else user.roles[0].role_id

    # 检查是否有活跃会话
    active_sid = await get_active_sid(user.userid)
    if active_sid:
        # 若有活跃会话，先删除旧会话
        await delete_session_sid(active_sid)

    sid = new_session_id()
    await add_user_session(user.userid, sid)
    await set_active_sid(user.userid, sid)
    
    # 创建访问令牌和刷新令牌
    access_token = create_access_token({"sub": user.userid, "sid": sid, "role_id": cur_role_id})
    refresh_token = create_refresh_token({"sub": user.userid, "sid": sid, "role_id": cur_role_id})

    # 将刷新令牌存储到Redis，用于验证和注销
    await set_session_kv(sid, "refresh_token", refresh_token)

    # 存储前端传入的SM2公钥
    await set_session_kv(sid, "cli_pubkey", payload.cli_pubkey)

    # 生成SM2密钥对，私钥存储在Redis，公钥返回给前端
    svr_privkey, svr_pubkey = gen_sm2_keypair()
    await set_session_kv(sid, "svr_privkey", svr_privkey)
    
    # 同时记录到应用日志
    auth_logger.info(
        "User logged in", 
        user_id=user.userid,
        username=user.username,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent", ""),
        phone_info=payload.phoneinfo
    )

    # 直接返回响应数据，让FastAPI自动处理响应创建
    # 这样可以确保CORS头等必要的头信息被正确设置
    return R.ok(data={
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "svr_pubkey": svr_pubkey,
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
        role_id = payload.get("role_id")
        
        if not user_id or not sid or not role_id:
            raise BizException(message="无效的刷新令牌")
        
        # 验证用户是否存在
        user = db.query(User).filter(User.userid == user_id).first()
        if not user:
            raise BizException(message="用户不存在")
        
        # 验证会话ID是否有效
        active_sid = await get_active_sid(user_id)
        if active_sid is None or active_sid != sid:
            raise BizException(message="会话已失效或在其他设备登录")
        
        # 验证存储的刷新令牌是否匹配（防止令牌重用）
        stored_refresh_token = await get_session_kv(sid, "refresh_token")
        if not stored_refresh_token or stored_refresh_token != refresh_token:
            raise BizException(message="无效的刷新令牌")
            
        # 生成新的访问令牌和刷新令牌
        new_access_token = create_access_token({"sub": user_id, "sid": sid, "role_id": role_id})
        new_refresh_token = create_refresh_token({"sub": user_id, "sid": sid, "role_id": role_id})
        
        await add_user_session(user_id, sid)
        await set_active_sid(user_id, sid)

        # 更新存储的刷新令牌
        await set_session_kv(sid, "refresh_token", new_refresh_token)

        await expire_session_sid(sid)
        
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


@router.post("/switchRole", response_model=R[TokenWithRefresh], dependencies=[Depends(RateLimiter(times=5, seconds=60))])
async def switch_role(
    role_id: str = Body(),
    cli_pubkey: str = Body(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not role_id:
        raise BizException(message="角色ID不能为空")

    if role_id not in [role.role_id for role in current_user.roles]:
        raise BizException(message="目标角色不存在")

    # 清除当前会话
    sid = getattr(current_user, "sid", None)
    if sid:
        await delete_session_sid(sid)
        # 清除 active_sid 指针
        if await get_active_sid(current_user.userid) == sid:
            await clear_active_sid(current_user.userid)

    new_sid = new_session_id()
    await add_user_session(current_user.userid, new_sid)
    await set_active_sid(current_user.userid, new_sid)

    # 携带新角色ID生成令牌
    access_token = create_access_token({"sub": current_user.userid, "sid": new_sid, "role_id": role_id})
    refresh_token = create_refresh_token({"sub": current_user.userid, "sid": new_sid, "role_id": role_id})

    # 更新Redis中的会话信息
    await set_session_kv(new_sid, "refresh_token", refresh_token)

    # 存储前端传入的SM2公钥
    await set_session_kv(new_sid, "cli_pubkey", cli_pubkey)

    # 生成SM2密钥对，私钥存储在Redis，公钥返回给前端
    svr_privkey, svr_pubkey = gen_sm2_keypair()
    await set_session_kv(new_sid, "svr_privkey", svr_privkey)

    return R.ok(data={
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "svr_pubkey": svr_pubkey,
    })


@router.post("/setDefaultRole", response_model=R[dict])
async def set_default_role(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    data = await request.json()
    role_id = data.get("role_id")
    if not role_id:
        raise BizException(message="角色ID不能为空")
    
    user = db.query(User).filter(User.userid == current_user.userid).first()
    if not user:
        raise BizException(message="用户不存在")

    if role_id not in [role.role_id for role in user.roles]:
        raise BizException(message="目标角色不存在")

    if role_id != current_user.role_id:
        raise BizException(message="不能将非当前角色设置为默认角色")

    if role_id == user.default_role_id:
        user.default_role_id = None
    else:
        user.default_role_id = role_id

    db.commit()
    db.refresh(user)
    
    return R.ok(message="默认角色设置成功", data={
        "default_role_id": user.default_role_id,
    })


@router.post("/logout", response_model=R[None])
async def logout(current_user: User = Depends(get_current_user)):
    sid = getattr(current_user, "sid", None)
    
    if not sid:
        raise BizException(code=401, message="会话不存在或已过期")

    await delete_session_sid(sid)
    # 只在当前 sid 为 active 时清空指针，防并发误删
    if await get_active_sid(current_user.userid) == sid:
        await clear_active_sid(current_user.userid)

    return R.ok(message="退出成功")


@router.get("/me", response_model=R[UserOut])
async def me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db), sm2_client= Depends(get_sm2_client)):
    user = db.query(User).filter(User.userid == current_user.userid).first()
    if not user:
        raise BizException(message="用户不存在")

    try:
        user_out = UserOut(
            userid=current_user.userid,
            username=current_user.username,
        )
        user_out.idcard = sm2_encrypt_hex(sm2_client, user.idcard) if user.idcard else None
        user_out.phone = sm2_encrypt_hex(sm2_client, user.phone) if user.phone else None
        user_out.name = sm2_encrypt_hex(sm2_client, user.name) if user.name else None

        cur_role = next((role for role in user.roles if role.role_id == current_user.role_id), None)
        user_out.role_id = current_user.role_id
        user_out.role_name = cur_role.role_name if cur_role else None
        user_out.role_code = cur_role.role_code if cur_role else None

        user_out.roles = [RoleOut.model_validate(role) for role in user.roles] if user.roles else None

        return R.ok(data=user_out)
    except Exception as e:
        raise BizException(message="获取用户信息失败")


@router.get("/getMenuTree", response_model=R)
async def get_menu_tree(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """获取菜单树"""
    try:
        # 查询所有菜单资源
        menu_resources : List[Resource] = db.query(Resource).filter(
            Resource.rtype == ResourceType.MENU,
            Resource.status == 1,
        ).order_by(Resource.sort).all()
        # 查询当前用户角色的权限
        grants : List[RoleAreaGrant] = db.query(RoleAreaGrant).filter(
            RoleAreaGrant.role_id == current_user.role_id,
            RoleAreaGrant.is_grant == 1
        ).all()
        granted_ids = {g.rid for g in grants}

        resources_by_parent: dict[str | None, List[Resource]] = {}
        for res in menu_resources:
            resources_by_parent.setdefault(res.parent_id, []).append(res)
        
        def has_permission(resource: Resource):
            return resource.rid in granted_ids
        
        def build_menu_node(resource: Resource):
            """递归构建菜单节点"""
            node = {
                "id": resource.rid,
                "name": resource.rname,
                "code": resource.rcode,
                "path": resource.path,
                "icon": resource.icon,
                "menuType": resource.menu_type,
                "children": [],
            }
            children = sorted(resources_by_parent.get(resource.rid, []), key=lambda x: x.sort or 0)
            for child in children:
                if has_permission(child):
                    node["children"].append(build_menu_node(child))
            return node
        
        # 构建菜单树
        menu_tree = []
        top_resources = sorted(resources_by_parent.get(None, []), key=lambda x: x.sort or 0)
        for res in top_resources:
            if has_permission(res):
                menu_tree.append(build_menu_node(res))
        
        return R.ok(data=menu_tree)
    except Exception as e:
        raise BizException(message="获取菜单树失败")


@router.get("/getButtonRight", response_model=R)
async def get_button_right(menu_code: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """获取按钮权限"""
    if not menu_code:
        raise BizException(message="菜单编码不能为空")

    menu = db.query(Resource).filter(Resource.rcode == menu_code).first()
    if not menu:
        raise BizException(message="菜单不存在")

    try:
        authorized_buttons = db.query(Resource).join(
            RoleAreaGrant,
            and_(
                Resource.rid == RoleAreaGrant.rid,
                RoleAreaGrant.role_id == current_user.role_id,
                RoleAreaGrant.is_grant == 1,
            ),
        ).filter(
            Resource.parent_id == menu.rid,
            Resource.rtype == ResourceType.BUTTON,
            Resource.status == 1,
        ).all()

        result = [
            {
                "id": res.rid,
                "name": res.rname,
                "code": res.rcode,
            }
            for res in authorized_buttons
        ]
        return R.ok(data=result)
    except Exception as e:
        auth_logger.error(f"获取按钮权限失败: {str(e)}")
        raise BizException(message="获取按钮权限失败")