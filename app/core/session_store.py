# app/core/session_store.py  （Drop-in 替换）
import asyncio
from uuid import uuid4
from typing import Optional
from app.core.config import settings
from app.db.redis_session import get_redis_client

SESSION_TTL_SECONDS = settings.SESSION_TTL_SECONDS

def new_session_id() -> str:
    return uuid4().hex

def _sessk(sid: str, field: str) -> str:
    return f"sess:{sid}:{field}"

def _user_sids_key(uid: str | int) -> str:
    return f"user:{uid}:sids"

def _active_sid_key(uid: str | int) -> str:
    return f"user:{uid}:active_sid"

async def set_active_sid(uid: str | int, sid: str, ttl: int = SESSION_TTL_SECONDS):
    r = get_redis_client()
    # active_sid 本身也设 TTL（方便无感过期）
    await r.set(_active_sid_key(uid), sid, ex=ttl)

async def get_active_sid(uid: str | int) -> Optional[str]:
    r = get_redis_client()
    return await r.get(_active_sid_key(uid))

async def clear_active_sid(uid: str|int):
    r = get_redis_client()
    await r.delete(_active_sid_key(uid))

# --- 按 sid 的 KV ---
async def set_session_kv(sid: str, field: str, value: str, ttl: int = SESSION_TTL_SECONDS):
    r = get_redis_client()
    await r.set(_sessk(sid, field), value, ex=ttl)

async def get_session_kv(sid: str, field: str) -> Optional[str]:
    r = get_redis_client()
    return await r.get(_sessk(sid, field))

async def expire_session_sid(sid: str, ttl: int = SESSION_TTL_SECONDS):
    r = get_redis_client()
    cursor = b'0'
    pattern = f"sess:{sid}:*"
    while True:
        cursor, keys = await r.scan(cursor=cursor, match=pattern, count=200)
        if keys:
            p = r.pipeline()
            for k in keys:
                p.expire(k, ttl)
            await p.execute()
        if cursor in (0, b'0'):
            break

async def delete_session_sid(sid: str):
    r = get_redis_client()
    uid = await r.get(_sessk(sid, "user"))
    cursor = b'0'
    pattern = f"sess:{sid}:*"
    while True:
        cursor, keys = await r.scan(cursor=cursor, match=pattern, count=200)
        if keys:
            await r.unlink(*keys)   # 非阻塞删除
        if cursor in (0, b'0'):
            break
    if uid:
        await r.srem(_user_sids_key(uid), sid)

# --- 用户 <-> sid 关系 ---
async def add_user_session(uid: str | int, sid: str, ttl: int = SESSION_TTL_SECONDS):
    r = get_redis_client()
    p = r.pipeline()
    p.set(_sessk(sid, "user"), str(uid), ex=ttl)
    p.sadd(_user_sids_key(uid), sid)
    await p.execute()

async def list_user_sids(uid: str | int) -> list[str]:
    r = get_redis_client()
    sids = await r.smembers(_user_sids_key(uid))
    return [s.decode() if isinstance(s, (bytes, bytearray)) else str(s) for s in (sids or [])]

async def clear_user_sessions(uid: str | int):
    r = get_redis_client()
    sids = await list_user_sids(uid)
    if not sids: return
    await asyncio.gather(*(delete_session_sid(s) for s in sids))
    await r.delete(_user_sids_key(uid))
