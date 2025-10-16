from app.core.config import settings
import redis.asyncio as redis
from typing import Optional

_redis: Optional[redis.Redis] = None

async def init_redis() -> redis.Redis:
    """在应用启动时调用，创建全局连接（或连接池）"""
    global _redis
    if _redis is None:
        _redis = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            retry_on_timeout=True,
            health_check_interval=30,
            encoding="utf-8",
        )
    return _redis

async def close_redis() -> None:
    """在应用关闭时调用"""
    global _redis
    if _redis is not None:
        await _redis.close()
        _redis = None

def get_redis_client() -> redis.Redis:
    """FastAPI 依赖函数用——拿到已经初始化的客户端"""
    if _redis is None:
        # 开发/测试没跑 startup 时给出明确提示
        raise RuntimeError("Redis not initialized. Call init_redis() on startup.")
    return _redis