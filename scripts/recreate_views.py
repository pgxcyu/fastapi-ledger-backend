#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
重新创建数据库视图的脚本

使用方法：
1. 确保Docker环境中的PostgreSQL数据库已启动
2. 运行此脚本：python scripts/recreate_views.py
"""

import os
import sys
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('recreate_views.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


# 用户交易摘要视图的SQL定义
USER_TRANSACTION_SUMMARY_VIEW_SQL = """
CREATE OR REPLACE VIEW user_transaction_summary AS
SELECT
    u.userid,  -- 用户ID
    u.username,  -- 用户名
    COUNT(t.transaction_id) AS total_transactions,  -- 总账单条数
    -- 收入总和（根据实际类型值调整条件）
    SUM(CASE WHEN t.type = 'INCOME' THEN t.amount ELSE 0 END) AS total_income,
    -- 支出总和（根据实际类型值调整条件）
    SUM(CASE WHEN t.type = 'EXPENSE' THEN t.amount ELSE 0 END) AS total_expense
FROM users u
LEFT JOIN transactions t ON t.create_userid = u.userid
GROUP BY u.userid, u.username;
"""


def recreate_views():
    """重新创建所有必要的视图"""
    try:
        # 从环境变量或默认值获取数据库连接信息
        db_url = os.getenv(
            "DATABASE_URL", 
            "postgresql+psycopg://postgres:152183312@localhost:5432/fastapi-ledger"
        )
        
        logger.info(f"开始重新创建数据库视图...")
        logger.info(f"连接数据库: {db_url}")
        
        # 创建数据库引擎
        engine = create_engine(db_url)
        
        with engine.connect() as conn:
            # 开始事务
            trans = conn.begin()
            
            try:
                # 首先删除可能存在的视图
                logger.info("删除旧的user_transaction_summary视图（如果存在）...")
                conn.execute(text("DROP VIEW IF EXISTS user_transaction_summary CASCADE"))
                
                # 删除旧版本的视图（如果存在）
                logger.info("删除旧版本的v_user_txn_summary视图（如果存在）...")
                conn.execute(text("DROP VIEW IF EXISTS v_user_txn_summary CASCADE"))
                
                # 创建新的视图
                logger.info("创建新的user_transaction_summary视图...")
                conn.execute(text(USER_TRANSACTION_SUMMARY_VIEW_SQL))
                
                # 提交事务
                trans.commit()
                logger.info("数据库视图创建成功！")
                
                # 验证视图是否创建成功
                logger.info("验证视图是否创建成功...")
                result = conn.execute(text("SELECT userid, username, total_transactions FROM user_transaction_summary LIMIT 1"))
                if result.fetchone():
                    logger.info("视图验证成功，可以正常查询！")
                else:
                    logger.info("视图验证成功，但当前可能没有用户数据。")
                    
            except Exception as e:
                # 发生错误时回滚事务
                trans.rollback()
                logger.error(f"创建视图时发生错误: {str(e)}")
                raise
        
    except SQLAlchemyError as e:
        logger.error(f"数据库错误: {str(e)}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"发生未知错误: {str(e)}")
        sys.exit(1)
    finally:
        # 关闭数据库连接
        if 'engine' in locals():
            engine.dispose()
            logger.info("数据库连接已关闭")


def main():
    """主函数"""
    try:
        recreate_views()
        logger.info("所有视图重新创建完成！")
    except Exception as e:
        logger.error(f"执行失败: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()