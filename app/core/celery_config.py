from celery import Celery
from app.core.config import settings
import os

# 创建Celery应用实例
# 使用环境变量覆盖默认配置，优先使用localhost以支持本地测试
broker_url = os.getenv("CELERY_BROKER_URL", settings.CELERY_BROKER_URL)
result_backend = os.getenv("CELERY_RESULT_BACKEND", settings.CELERY_RESULT_BACKEND)

# 如果环境变量未设置且默认URL包含"redis://redis"，则替换为localhost
if "redis://redis" in broker_url:
    broker_url = broker_url.replace("redis://redis", "redis://localhost")
if "redis://redis" in result_backend:
    result_backend = result_backend.replace("redis://redis", "redis://localhost")

# 添加日志输出，查看实际使用的URL
print(f"Celery使用的Broker URL: {broker_url}")
print(f"Celery使用的Result Backend URL: {result_backend}")

celery_app = Celery(
    "fastapi-ledger",
    broker=broker_url,
    backend=result_backend,
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
