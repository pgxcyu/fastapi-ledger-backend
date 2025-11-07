from celery import Celery
from app.core.config import settings
import os

# 创建Celery应用实例
celery_app = Celery(
    "fastapi-ledger",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=['app.tasks.celery_tasks'],
)

# 其他配置
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    # 设置任务结果保留时间为7天（单位：秒）
    result_expires=3600*24*7,
    # 确保任务结果持久化保存
    result_persistent=True,
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
