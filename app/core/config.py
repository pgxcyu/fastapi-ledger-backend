# app/core/config.py
import os
import json

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# 加载 .env 文件中的环境变量
load_dotenv()

class Settings(BaseSettings):
    # 项目根目录
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # 安全配置
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))   
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    # 数据库配置
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    SQLALCHEMY_DATABASE_URL: str = os.getenv("SQLALCHEMY_DATABASE_URL", "postgresql+psycopg://postgres:152183312@127.0.0.1:5432/fastapi-ledger")

    SESSION_TTL_SECONDS: int = int(os.getenv("SESSION_TTL_SECONDS", "2592000"))  # 30 天

    # 孤儿文件配置
    UPLOAD_DIR: str = os.path.join(BASE_DIR, "app/static/upload_files")
    QUARANTINE_DIR: str = os.path.join(BASE_DIR, "app/static/quarantine")
    UNTRACKED_FS_RETENTION_DAYS: int = int(os.getenv("UNTRACKED_FS_RETENTION_DAYS", "2"))     # 磁盘未入库保留期
    UNLINKED_DB_RETENTION_DAYS: int = int(os.getenv("UNLINKED_DB_RETENTION_DAYS", "2"))      # DB 未绑定保留期
    QUARANTINE_LIFETIME_DAYS: int = int(os.getenv("QUARANTINE_LIFETIME_DAYS", "7"))      # 隔离区保留天数
    CLEANUP_CRON: str = os.getenv("CLEANUP_CRON", "30 3 * * *")       # 每天 03:30

    # 签名配置
    SIGNING_KEYS: dict = json.loads(os.getenv("SIGNING_KEYS", '{"app_ledger_v1":"zowiesoft"}'))

    # 日志配置
    LOG_DIR: str = os.getenv("LOG_DIR", "logs")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_TO_CONSOLE: bool = bool(int(os.getenv("LOG_TO_CONSOLE", "0")))

    # SM2 非登录密钥
    SM2_PRIVATE_KEY_NOLOGIN: str = os.getenv("SM2_PRIVATE_KEY_NOLOGIN")
    SM2_PUBLIC_KEY_NOLOGIN: str = os.getenv("SM2_PUBLIC_KEY_NOLOGIN")

# 创建全局 settings 实例
settings = Settings()
