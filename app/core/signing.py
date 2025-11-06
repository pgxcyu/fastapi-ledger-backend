# app/core/signing.py
import base64
import hashlib
import hmac
import json
import time
from typing import Any, Optional

from fastapi import Depends, HTTPException, Header, Request

from app.core.exceptions import BizException

SIGN_WINDOW = 180  # 秒

ISDEBUG = False

def debug_print(msg: str):
    if ISDEBUG:
        print(msg)

def _stable(obj: Any) -> Any:
    if obj is None: return None
    if isinstance(obj, (str,int,float,bool)): return obj
    if isinstance(obj, list): return [_stable(i) for i in obj]
    if isinstance(obj, dict):
        # 与前端 stableStringify 保持一致地忽略动态字段
        IGNORES = {"timestamp","ts","_","_t","nonce","create_time","created_at","update_time","updated_at"}
        return {k:_stable(obj[k]) for k in sorted(obj.keys()) if k not in IGNORES}
    return str(obj)

def json_canon_dump(obj: Any) -> str:
    return json.dumps(_stable(obj), ensure_ascii=False, separators=(',',':'))

def canonicalize_query(req: Request) -> str:
    # 与前端canonicalizeQuery保持一致的实现
    query_string = req.url.query
    if not query_string:
        return ''
    
    # 分割键值对并解码
    kvs = []
    for param in query_string.split('&'):
        if not param:
            continue
        parts = param.split('=', 1)
        key = parts[0]
        value = parts[1] if len(parts) > 1 else ''
        # 解码键值对
        from urllib.parse import unquote
        key_decoded = unquote(key)
        value_decoded = unquote(value)
        kvs.append((key_decoded, value_decoded))
  
    # 排序 - 先按键排序，键相同时按值排序
    kvs.sort(key=lambda x: (x[0], x[1]))
  
    # 重新编码并构建查询字符串
    from urllib.parse import quote
    return '&'.join([f"{quote(k)}={quote(v)}" for k, v in kvs])

def get_secret_by_kid(kid: str) -> Optional[str]:
    # 建议配置在 settings.SIGNING_KEYS = {"app_ledger_v1":"zowiesoft", ...}
    from app.core.config import settings
    debug_print(f"调试信息 - SIGNING_KEYS配置: {settings.SIGNING_KEYS}")
    debug_print(f"调试信息 - 查询kid: {kid}")
    result = settings.SIGNING_KEYS.get(kid)
    debug_print(f"调试信息 - 密钥查询结果: {result}")
    return result

async def verify_signature(
    request: Request,
    x_key_id: str = Header(..., alias="X-Key-Id"),
    x_timestamp: str = Header(..., alias="X-Timestamp"),
    x_nonce: str = Header(..., alias="X-Nonce"),
    x_body_hash: str = Header('', alias="X-Body-Hash"),
    x_signature: str = Header(..., alias="X-Signature"),
    idem: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    debug_print(f"调试信息 - 接收到的请求头:")
    debug_print(f"X-Key-Id: {x_key_id}")
    debug_print(f"X-Timestamp: {x_timestamp}")
    debug_print(f"X-Nonce: {x_nonce}")
    debug_print(f"X-Signature: {x_signature}")
    
    # 1) 时间窗
    try:
        ts = int(x_timestamp)
        debug_print(f"调试信息 - 时间戳转换成功: {ts}")
    except Exception as e:
        debug_print(f"调试信息 - 时间戳转换失败: {e}")
        raise BizException(code=40101, message="无效的时间戳")
  
    current_time = int(time.time())
    time_diff = abs(current_time - ts)
    debug_print(f"调试信息 - 当前时间: {current_time}, 时间差: {time_diff}, 窗口: {SIGN_WINDOW}")
  
    if time_diff > SIGN_WINDOW:
        raise BizException(code=40101, message="时间戳过期")

    # 2) 防重放：kid+nonce 5 分钟唯一
    redis = getattr(request.app.state, "redis", None)
    debug_print(f"调试信息 - Redis可用: {redis is not None}")
    if redis:
        rkey = f"sig:{x_key_id}:{x_nonce}"
        debug_print(f"调试信息 - 检查重放键: {rkey}")
    if await redis.exists(rkey):
      raise BizException(code=40101, message="重放检测")
    await redis.setex(rkey, 300, "1")

    # 3) 取密钥
    secret = get_secret_by_kid(x_key_id)
    debug_print(f"调试信息 - 获取密钥: {secret}")
    if not secret:
        raise BizException(code=40101, message="未知的密钥ID")

    # 4) 组 canonical
    method = request.method.upper()
    # 规范化路径，确保与前端normalizePath行为一致
    path_only = request.url.path.rstrip('/')  # 移除尾部斜杠
    # 移除查询参数和fragment
    if '?' in path_only:
        path_only = path_only.split('?')[0]
    query_canon = canonicalize_query(request)

    body_hash = x_body_hash or ""
    if method != "GET":
        try:
            body = await request.json()
            body_hash_srv = hashlib.sha256(json_canon_dump(body).encode("utf-8")).hexdigest()
        except Exception:
            raw = await request.body()  # 非 JSON 的容错
            body_hash_srv = hashlib.sha256(raw or b"").hexdigest()
        if body_hash and body_hash.lower() != body_hash_srv.lower():
            raise BizException(code=40101, message="请求体哈希不匹配") 
        body_hash = body_hash or body_hash_srv

    canonical = "\n".join([
        method, path_only, query_canon, body_hash, x_timestamp, x_nonce, (idem or ""), x_key_id
    ])
    debug_print(f"调试信息 - 构建的canonical字符串:\n{canonical}")
  
    expected = base64.b64encode(hmac.new(secret.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256).digest()).decode()
    debug_print(f"调试信息 - 计算的签名: {expected}")
    debug_print(f"调试信息 - 接收到的签名: {x_signature}")

    if not hmac.compare_digest(expected, x_signature):
        debug_print("调试信息 - 签名验证失败")
        raise BizException(code=40101, message="签名验证失败")

    request.state.sign_verified = True
