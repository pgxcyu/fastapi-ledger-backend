import os

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

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

# 辅助函数：从字符串解析crontab表达式
def crontab_from_string(cron_string):
    """将cron字符串(如 '30 3 * * *') 转换为Celery的crontab对象"""
    parts = cron_string.split()
    if len(parts) != 5:
        raise ValueError(f"无效的cron表达式: {cron_string}")
    return crontab(
        minute=parts[0],
        hour=parts[1],
        day_of_month=parts[2],
        month_of_year=parts[3],
        day_of_week=parts[4]
    )

celery_app.conf.beat_schedule = {
    'cleanup-files-daily': {
        'task': 'app.tasks.celery_tasks.cleanup_files_task',
        'schedule': crontab_from_string(settings.CLEANUP_CRON),
        'args': (False,),  # 不使用dry_run模式
    },
}


# 日志配置 - 确保Celery日志写入到项目日志目录
beat_log_path = os.path.join(settings.LOG_DIR, 'celery-beat.log')
worker_log_path = os.path.join(settings.LOG_DIR, 'celery-worker.log')

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
    # 日志配置
    worker_log_format="%(asctime)s - %(levelname)s - [%(processName)s:%(process)d] %(message)s",
    worker_task_log_format="%(asctime)s - %(levelname)s - [%(processName)s:%(process)d][%(task_name)s(%(task_id)s)] %(message)s",
    beat_log_format="%(asctime)s - %(levelname)s - [%(processName)s:%(process)d] %(message)s",
    # 确保日志级别与项目配置一致
    worker_log_level=settings.LOG_LEVEL.lower(),
    beat_log_level=settings.LOG_LEVEL.lower(),
    # Beat选项
    beat_max_loop_interval=15,  # 最大循环间隔（秒），避免CPU占用过高
    beat_scheduler='celery.beat.PersistentScheduler',
    beat_schedule_filename='celerybeat-schedule.db',  # 存储最后一次执行时间的文件
)
