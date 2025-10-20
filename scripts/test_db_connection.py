#!/usr/bin/env python3
# 测试数据库连接脚本

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

# 加载环境变量
load_dotenv()

def test_db_connection():
    """测试PostgreSQL数据库连接"""
    try:
        # 从环境变量获取数据库URL
        db_url = os.getenv("SQLALCHEMY_DATABASE_URL", "postgresql+psycopg://postgres:152183312@localhost:5432/fastapi-ledger")
        print(f"尝试连接到数据库: {db_url}")
        
        # 创建数据库引擎
        engine = create_engine(db_url)
        
        # 尝试连接
        with engine.connect() as connection:
            print("✅ 数据库连接成功!")
            # 测试简单查询
            result = connection.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"📦 PostgreSQL版本: {version}")
            return True
    
    except OperationalError as e:
        print(f"❌ 数据库连接失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 发生错误: {e}")
        return False

if __name__ == "__main__":
    print("开始测试数据库连接...")
    success = test_db_connection()
    print(f"测试结果: {'成功' if success else '失败'}")