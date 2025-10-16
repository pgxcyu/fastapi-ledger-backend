from .models import Base
from .session import engine

def init_db():
    # 创建所有表
    Base.metadata.create_all(bind=engine)

# 如果直接运行此文件，则初始化数据库
if __name__ == "__main__":
    init_db()
