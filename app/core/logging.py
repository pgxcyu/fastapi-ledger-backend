# app/core/logging.py
import logging, json, os
from logging.handlers import TimedRotatingFileHandler
from app.core.config import settings

class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord):
        payload = {
            "ts": int(record.created * 1000),
            "level": record.levelname,
            "msg": record.getMessage(),
            "logger": record.name,
        }
        for k in ("request_id", "path", "method", "status_code", "elapsed_ms", "user_id", "ip"):
            v = getattr(record, k, None)
            if v is not None: payload[k] = v
        return json.dumps(payload, ensure_ascii=False)

def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def _make_rotating_handler(filename: str, level: int, formatter: logging.Formatter):
    """
    每天 0 点轮转，保留 7 天；UTF-8；线程安全。
    """
    handler = TimedRotatingFileHandler(
        filename, when="midnight", backupCount=7, encoding="utf-8", utc=False
    )
    handler.setLevel(level)
    handler.setFormatter(formatter)
    return handler

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
    root_level = getattr(logging, level_name, logging.INFO)

    fmt = JSONFormatter()

    # 文件
    h_app_file   = _make_rotating_handler(os.path.join(log_dir, "app.log"),   logging.INFO,  fmt)
    h_error_file = _make_rotating_handler(os.path.join(log_dir, "error.log"), logging.ERROR, fmt)
    h_access_file= _make_rotating_handler(os.path.join(log_dir, "access.log"), logging.INFO, fmt)

    # Root：业务 & 框架日志（不含访问日志）
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(root_level)
    root.addHandler(h_app_file)
    root.addHandler(h_error_file)

    # 访问日志：单独 logger，避免和业务日志混在一起
    access_logger = logging.getLogger("access")
    access_logger.handlers.clear()
    access_logger.setLevel(logging.INFO)
    access_logger.addHandler(h_access_file)
    access_logger.propagate = False         # 不向上冒泡到 root，防止重复记录

    # 控制台
    if settings.LOG_TO_CONSOLE:
        h_console = logging.StreamHandler()
        h_console.setLevel(root_level)
        h_console.setFormatter(fmt)
        root.addHandler(h_console)
        access_logger.addHandler(h_console)     # 开发期希望也看到访问日志；线上可去掉

    # 其他业务子 logger（可按需添加）
    for name in ("auth", "csrf", "security"):
        lg = logging.getLogger(name)
        lg.propagate = True                 # 让它们走 root 的 app.log / error.log
        lg.setLevel(root_level)
