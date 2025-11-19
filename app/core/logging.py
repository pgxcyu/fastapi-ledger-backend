# app/core/logging.py
from datetime import datetime
import json
import logging
import os
from pathlib import Path
import sys

from loguru import logger

from app.core.config import settings
from app.core.request_ctx import get_request_id, get_user_context

# 移除loguru的默认处理器
logger.remove()

# 确保日志目录存在
def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

class InterceptHandler(logging.Handler):
    """把标准 logging 的日志转发到 loguru，统一出口"""
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except Exception:
            level = record.levelno
        logger.opt(depth=6, exception=record.exc_info).log(level, record.getMessage())

# 设置日志配置
def setup_logging():
    """
    日志落地策略：
      - 控制台：所有等级（开发期方便）
      - logs/app.log：INFO+
      - logs/error.log：ERROR+
      - logs/access.log：仅 access 访问日志（INFO+）
    """
    log_dir = getattr(settings, "LOG_DIR", None) or os.getenv("LOG_DIR", "logs")
    _ensure_dir(log_dir)
    
    # 读取日志等级（默认 INFO）
    level_name = (getattr(settings, "LOG_LEVEL", None) or os.getenv("LOG_LEVEL", "INFO")).upper()
    level_name = level_name if level_name in ["TRACE","DEBUG","INFO","WARNING","ERROR","CRITICAL"] else "INFO"

    # 轮转/保留
    rotation  = "00:00"      # 每天 0 点轮转
    retention = "7 days"     # 保留7天
    enqueue = True           # 多进程/线程安全
    
    # 定义日志过滤器函数，使逻辑更清晰
    def app_filter(record):
        """应用日志过滤器：排除访问日志"""
        extra = record.get("extra", {})
        if not isinstance(extra, dict):
            return True
        return extra.get("logger") != "access"
    
    def access_filter(record):
        """访问日志过滤器：只包含访问日志"""
        extra = record.get("extra", {})
        if not isinstance(extra, dict):
            return False
        return extra.get("logger") == "access"
    
    
    # 配置应用日志（INFO+）- 排除访问日志
    app_log_path = os.path.join(log_dir, "app.log")
    logger.add(
        app_log_path,
        level=level_name,
        rotation=rotation,
        retention=retention,
        backtrace=True,
        diagnose=True,
        enqueue=enqueue,
        filter=app_filter,
        serialize=True,
        delay=True,  # 延迟文件创建，直到第一次写入时才打开文件
    )
    
    # 配置错误日志（ERROR+）
    error_log_path = os.path.join(log_dir, "error.log")
    logger.add(
        error_log_path,
        level="ERROR",
        rotation=rotation,
        retention=retention,
        backtrace=True,
        diagnose=True,
        enqueue=enqueue,
        filter=app_filter,
        serialize=True,
        delay=True,
    )
    
    # 配置访问日志（INFO+）- 只包含访问日志
    access_log_path = os.path.join(log_dir, "access.log")
    logger.add(
        access_log_path,
        level="INFO",
        rotation=rotation,
        retention=retention,
        backtrace=False,
        diagnose=False,
        enqueue=enqueue,
        filter=access_filter,
        serialize=True,
        delay=True,
    )
    
    # 控制台日志（开发环境）
    if getattr(settings, "LOG_TO_CONSOLE", True):
        logger.add(
            sys.stdout,
            level=level_name,
            colorize=True,
            backtrace=True,
            diagnose=True,
            format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
        )
    
    # —— 注入上下文（仅在不存在时补默认值，避免覆盖 bind 的值）——
    def inject_context(record):
        extra = record["extra"]
        if "request_id" not in extra:
            extra["request_id"] = get_request_id() or "-"
        uid, sid, role_id = get_user_context()
        if "user_id" not in extra or extra["user_id"] is None:
            extra["user_id"] = uid or "-"
        if "sid" not in extra or extra["sid"] is None:
            extra["sid"] = sid or "-"
        if "role_id" not in extra or extra["role_id"] is None:
            extra["role_id"] = role_id or "-"

    logger.configure(patcher=inject_context)

    # —— 接管标准 logging（uvicorn/fastapi/sqlalchemy 等）——
    logging.root.handlers = [InterceptHandler()]
    logging.root.setLevel(logging.INFO)
    # 扩展日志器名称列表，确保覆盖所有Celery相关日志
    celery_loggers = [
        "celery", "celery.task", "celery.worker", "celery.beat", 
        "celery.app.trace", "celery.worker.consumer", "celery.worker.strategy"
    ]
    other_loggers = [
        "uvicorn", "uvicorn.error", "uvicorn.access", "fastapi", 
        "sqlalchemy", "alembic", "apscheduler", "websockets"
    ]
    
    # 配置所有日志器
    for name in celery_loggers + other_loggers:
        logger_instance = logging.getLogger(name)
        logger_instance.handlers = [InterceptHandler()]
        logger_instance.propagate = False
        # 为Celery相关日志设置适当的日志级别
        if name in celery_loggers:
            logger_instance.setLevel(getattr(logging, level_name))

# 为了兼容现有代码，提供get_logger函数
def get_logger(name: str = None) -> logger:
    """获取logger实例，支持命名"""
    if name:
        return logger.bind(logger=name)
    return logger

# 各种日志类型的logger
access_logger = logger.bind(logger="access")
auth_logger = logger.bind(logger="auth")
middleware_logger = logger.bind(logger="middleware")
cleanup_logger = logger.bind(logger="cleanup")

# 导出logger以供直接使用
__all__ = [
    "logger",
    "get_logger",
    "access_logger",
    "auth_logger",
    "middleware_logger",
    "cleanup_logger",
    "setup_logging"
]
