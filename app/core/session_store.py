import os
import time
from uuid import uuid4

from app.core.config import settings
from app.db.redis_session import get_redis_client


SESSION_TTL_SECONDS = settings.SESSION_TTL_SECONDS

async def new_session_id() -> str:
    # 注意：这个函数其实不需要异步，这里保持异步是为了API一致性
    return uuid4().hex


async def set_user_session(user_id: int | str, sid: str, ttl: int = SESSION_TTL_SECONDS):
    redis_client = get_redis_client()
    await redis_client.set(f"user:{user_id}:sid", sid, ex=ttl)


async def get_user_session(user_id: int | str) -> str | None:
    redis_client = get_redis_client()
    return await redis_client.get(f"user:{user_id}:sid")


async def clear_user_session(user_id: int | str):
    redis_client = get_redis_client()
    await redis_client.delete(f"user:{user_id}:sid")
    # 删除用户的所有会话数据
    keys = await redis_client.keys(f"user:{user_id}:data:*")
    if keys:
        await redis_client.delete(*keys)


async def set_user_session_data(user_id: int | str, key: str, value: str, ttl: int = SESSION_TTL_SECONDS):
    """设置用户会话数据"""
    redis_client = get_redis_client()
    await redis_client.set(f"user:{user_id}:data:{key}", value, ex=ttl)


async def get_user_session_data(user_id: int | str, key: str) -> str | None:
    """获取用户会话数据"""
    redis_client = get_redis_client()
    return await redis_client.get(f"user:{user_id}:data:{key}")
