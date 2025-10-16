# app/core/signing.py
import time, hmac, base64, hashlib, json
from typing import Optional, Any
from fastapi import Header, Request, HTTPException, Depends

from app.core.exceptions import BizException

SIGN_WINDOW = 180  # 秒

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
  items = sorted(req.query_params.multi_items())
  from urllib.parse import urlencode, quote
  return urlencode(items, doseq=True, quote_via=quote)

def get_secret_by_kid(kid: str) -> Optional[str]:
  # 建议配置在 settings.SIGNING_KEYS = {"app_ledger_v1":"zowiesoft", ...}
  from app.core.config import settings
  return settings.SIGNING_KEYS.get(kid)

async def verify_signature(
  request: Request,
  x_key_id: str = Header(..., alias="X-Key-Id"),
  x_timestamp: str = Header(..., alias="X-Timestamp"),
  x_nonce: str = Header(..., alias="X-Nonce"),
  x_body_hash: str = Header('', alias="X-Body-Hash"),
  x_signature: str = Header(..., alias="X-Signature"),
  idem: Optional[str] = Header(None, alias="Idempotency-Key"),
):
  # 1) 时间窗
  try:
    ts = int(x_timestamp)
  except:
    raise BizException(code=40101, message="无效的时间戳")
  if abs(int(time.time()) - ts) > SIGN_WINDOW:
    raise BizException(code=40101, message="时间戳过期")

  # 2) 防重放：kid+nonce 5 分钟唯一
  redis = getattr(request.app.state, "redis", None)
  if redis:
    rkey = f"sig:{x_key_id}:{x_nonce}"
    if await redis.exists(rkey):
      raise BizException(code=40101, message="重放检测")
    await redis.setex(rkey, 300, "1")

  # 3) 取密钥
  secret = get_secret_by_kid(x_key_id)
  if not secret:
    raise BizException(code=40101, message="未知的密钥ID")

  # 4) 组 canonical
  method = request.method.upper()
  path_only = request.url.path
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
  expected = base64.b64encode(hmac.new(secret.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256).digest()).decode()

  if not hmac.compare_digest(expected, x_signature):
    raise BizException(code=40101, message="签名验证失败")

  request.state.sign_verified = True
