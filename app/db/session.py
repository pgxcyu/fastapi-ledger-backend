from sqlalchemy.orm.session import Session


from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URL,
    pool_pre_ping = True,
    pool_size = 5,
    max_overflow = 20,
    pool_recycle = 1800,
    pool_use_lifo=True,
    future = True,
    # 添加连接超时设置，避免长时间等待连接
    connect_args={
        "connect_timeout": 10  # 连接超时时间，单位为秒
    }
)
SessionLocal = sessionmaker[Session](autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
