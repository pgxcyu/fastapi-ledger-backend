from celery import Celery
from app.core.config import settings
import os

# 创建Celery应用实例
celery_app = Celery(
    "fastapi-ledger",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=['app.tasks.celery_tasks'],
)

# 其他配置
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    # 增加任务超时设置
    task_time_limit=3600,
    task_soft_time_limit=1800,
    # 增加重试配置
    task_track_started=True,
    task_acks_late=True,
    # 增加连接池配置
    broker_pool_limit=10,
    broker_connection_timeout=30,
    broker_connection_retry=True,
    broker_connection_retry_on_startup=True,
)
