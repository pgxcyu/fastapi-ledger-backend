# pip install redis.asyncio 已在你项目里
import json, time, hashlib
from typing import Optional, Tuple
from fastapi import Request, Header, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.datastructures import Headers
from app.core.deps import get_current_user
from app.core.exceptions import BizException
from app.db.models import User
from app.core.config import settings
from app.db.redis_session import get_redis_client
from app.schemas import response
from app.schemas.response import R

IDEMP_TTL_SECONDS = 10 * 60  # 幂等键保存 10 分钟（可按需调大）
PROCESSING_TTL = 60        # processing 的占位时长（短一点）

def _hash_body(raw: bytes) -> str:
    return hashlib.sha256(raw or b"").hexdigest()

def _key(scope_user: str, path: str, idem_key: str) -> str:
    return f"idemp:{scope_user}:{path}:{idem_key}"

async def ensure_idempotency(
    request: Request,
    x_idem: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    redis = Depends(get_redis_client),
) -> Tuple[str, Optional[dict]]:
    """
    - 首次：落一条 {status:processing, req_hash, at} 并返回 (redis_key, None)
    - 重复：如同一 req_hash 已完成，则返回 (redis_key, cached_response)
    - 冲突：相同 Idempotency-Key 但 body 不同 → 409
    """
    if not x_idem:
        raise BizException(code=400, message="Missing Idempotency-Key")

    raw = await request.body()
    req_hash = _hash_body(raw)
    rk = _key(str(current_user.userid), request.url.path, x_idem)

    # 尝试首次登记
    payload = json.dumps({
        "status": "processing",
        "req_hash": req_hash,
        "started": int(time.time()),
    })

    # ✅ 只在创建时设置 TTL（SET NX EX 原子操作）
    created = await redis.set(rk, payload, ex=PROCESSING_TTL, nx=True)

    if created:
        # 首次请求
        request.state.idemp_key = rk
        request.state.idemp_hash = req_hash
        return rk, None

    # 已存在 → 读出记录
    data_raw = await redis.get(rk)
    data = json.loads(data_raw or "{}")
    if data.get("req_hash") != req_hash:
        raise BizException(code=409, message="Idempotency-Key conflict")

    # 已完成则重放响应
    if data.get("status") == "done" and "response" in data:
        sc = int(data.get("status_code") or 200)
        return rk, JSONResponse(status_code=sc, content=data["response"])

    raise BizException(code=409, message="Idempotent request is processing")


# —— 成功/可确定错误：固化结果，后续重放 —— #
async def idem_done(
    request: Request,
    response_obj,            # dict 或 Pydantic 模型
    status_code: int = 200,  # 保存原 HTTP 码
):
    redis = await get_redis_client()
    rk: str = getattr(request.state, "idemp_key", "")
    req_hash: str = getattr(request.state, "idemp_hash", "")
    if not rk or not req_hash:
        return

    try:
        if hasattr(response_obj, "model_dump"):
            resp_dict = response_obj.model_dump(mode="json")
        else:
            resp_dict = response_obj if isinstance(response_obj, dict) else json.loads(json.dumps(response_obj, default=str))
    except Exception:
        resp_dict = {"message": str(response_obj)}

    payload = {
        "status": "done",
        "req_hash": req_hash,
        "response": resp_dict,
        "status_code": status_code,       # ✅ 记住 HTTP 状态
        "at": int(time.time()),
    }
    await redis.set(rk, json.dumps(payload), ex=IDEMP_TTL_SECONDS)


# —— 系统异常/不确定结果：解锁，允许重试 —— #
async def idem_unlock(request: Request):
    redis = await get_redis_client()
    rk: str = getattr(request.state, "idemp_key", "")
    if rk:
        try:
            await redis.delete(rk)
        except Exception:
            pass


# 兼容你原来的保存函数（保留但不推荐只用它）
async def save_idempotency_response(request: Request, response_obj):
    # 等价 done(…, 200)
    await idem_done(request, response_obj, status_code=200)