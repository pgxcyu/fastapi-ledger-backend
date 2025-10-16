from sqlalchemy import create_engine, text

# 创建数据库引擎
engine = create_engine('sqlite:///app.db')

# 连接到数据库并删除临时表
try:
    with engine.connect() as conn:
        # 使用text()函数包装原始SQL字符串
        print("删除临时表_alembic_tmp_transactions...")
        conn.execute(text("DROP TABLE IF EXISTS _alembic_tmp_transactions"))
        conn.commit()
        print("临时表已成功删除。")
except Exception as e:
    print(f"删除临时表时出错: {e}")

print("清理完成。")