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

async def check_replay_time_window(redis, rkey: str, time_window: int, method: str) -> None:
    """
    检查重放请求的时间窗口
    
    Args:
        redis: Redis客户端
        rkey: 重放检测键
        time_window: 允许的时间窗口（秒）
        method: HTTP方法（用于调试信息）
    
    Raises:
        BizException: 如果超出时间窗口
    """
    debug_print(f"调试信息 - {method}请求使用时间窗口: {time_window}秒")
    
    # 获取第一次请求的时间戳
    first_request_time = await redis.get(rkey)
    if first_request_time:
        try:
            first_time = int(first_request_time)
            current_time = int(time.time())
            time_diff = current_time - first_time
            
            debug_print(f"调试信息 - 首次请求时间: {first_time}, 当前时间: {current_time}, 时间差: {time_diff}")
            
            # 如果在时间窗口内重复，可能是网络重试，允许通过
            if time_diff <= time_window:
                debug_print(f"调试信息 - 允许{method}请求重试（{time_window}秒内重复）")
            else:
                raise BizException(code=40101, message="重放检测")
        except (ValueError, TypeError):
            # 如果无法解析时间戳，按重放处理
            raise BizException(code=40101, message="重放检测")
    else:
        raise BizException(code=40101, message="重放检测")

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
    
    # 获取请求方法（统一获取，避免重复）
    method = request.method.upper()
    debug_print(f"调试信息 - 请求方法: {method}")
    
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

    # 2) 防重放：kid+nonce 5 分钟唯一，但允许 token 刷新重试
    redis = getattr(request.app.state, "redis", None)
    debug_print(f"调试信息 - Redis可用: {redis is not None}")
    if redis:
        rkey = f"sig:{x_key_id}:{x_nonce}"
        debug_print(f"调试信息 - 检查重放键: {rkey}")
        
        # 检查是否是重放请求
        if await redis.exists(rkey):
            debug_print(f"调试信息 - 发现重复nonce: {x_nonce}")
            
            # 对于 GET 请求，只使用时间窗口检查（不检查 Idempotency-Key）
            if method == "GET":
                # GET 请求使用更宽松的时间窗口（5秒）
                await check_replay_time_window(redis, rkey, 5, method)
            
            # 对于 POST/PUT/DELETE 请求，使用双重验证机制
            else:
                # 方案1：如果有 Idempotency-Key，检查幂等键
                if idem:
                    idem_key = f"idem:{idem}"
                    idem_exists = await redis.exists(idem_key)
                    debug_print(f"调试信息 - 检查幂等键: {idem_key}, 存在: {idem_exists}")
                    
                    if idem_exists:
                        debug_print("调试信息 - 允许 token 刷新重试（通过幂等键验证）")
                    else:
                        raise BizException(code=40101, message="重放检测")
                else:
                    # 方案2：检查是否是短时间内重复请求（token 刷新重试）
                    await check_replay_time_window(redis, rkey, 30, method)
        
        # 设置重放检测键，存储当前时间戳
        # GET 请求使用更短的过期时间（1分钟），其他请求使用5分钟
        expiry = 60 if method == "GET" else 300
        debug_print(f"调试信息 - 设置重放键过期时间: {expiry}秒")
        await redis.setex(rkey, expiry, str(int(time.time())))
        
        # 只有 POST/PUT/DELETE 请求且提供了 Idempotency-Key 时才设置幂等键
        # GET 请求不需要幂等键，因为它们天然是幂等的
        if method != "GET" and idem:
            idem_key = f"idem:{idem}"
            idem_expiry = 30  # POST/PUT/DELETE 请求的幂等键过期时间
            debug_print(f"调试信息 - 设置幂等键: {idem_key}, 过期时间: {idem_expiry}秒")
            await redis.setex(idem_key, idem_expiry, "1")

    # 3) 取密钥
    secret = get_secret_by_kid(x_key_id)
    debug_print(f"调试信息 - 获取密钥: {secret}")
    if not secret:
        raise BizException(code=40101, message="未知的密钥ID")

    # 4) 组 canonical
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
