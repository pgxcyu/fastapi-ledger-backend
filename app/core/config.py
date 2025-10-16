# app/core/config.py
import os

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
    SQLALCHEMY_DATABASE_URL: str = os.getenv("SQLALCHEMY_DATABASE_URL", "sqlite:///./app.db")

    SESSION_TTL_SECONDS: int = int(os.getenv("SESSION_TTL_SECONDS", "2592000"))  # 30 天

    # 孤儿文件配置
    UPLOAD_DIR: str = os.path.join(BASE_DIR, "app/static/upload_files")
    QUARANTINE_DIR: str = os.path.join(BASE_DIR, "app/static/quarantine")
    UNTRACKED_FS_RETENTION_DAYS: int = int(os.getenv("UNTRACKED_FS_RETENTION_DAYS", "2"))     # 磁盘未入库保留期
    UNLINKED_DB_RETENTION_DAYS: int = int(os.getenv("UNLINKED_DB_RETENTION_DAYS", "2"))      # DB 未绑定保留期
    QUARANTINE_LIFETIME_DAYS: int = int(os.getenv("QUARANTINE_LIFETIME_DAYS", "7"))      # 隔离区保留天数
    CLEANUP_CRON: str = os.getenv("CLEANUP_CRON", "30 3 * * *")       # 每天 03:30

    # 签名配置
    SIGNING_KEYS: dict = os.getenv("SIGNING_KEYS", {"app_ledger_v1":"zowiesoft"})

# 创建全局 settings 实例
settings = Settings()
