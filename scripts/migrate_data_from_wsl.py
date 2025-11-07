#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据迁移脚本：从WSL中的PostgreSQL数据库迁移数据到当前数据库

使用方法：
1. 确保WSL中的PostgreSQL数据库正在运行
2. 确保当前Docker环境中的PostgreSQL数据库已启动
3. 运行此脚本：python scripts/migrate_data_from_wsl.py
"""

import os
import sys
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('migration.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class DataMigrator:
    def __init__(self,
                 source_db_url: str,
                 target_db_url: str):
        """初始化数据迁移器"""
        self.source_engine = create_engine(source_db_url)
        self.target_engine = create_engine(target_db_url)
        self.SourceSession = sessionmaker(bind=self.source_engine)
        self.TargetSession = sessionmaker(bind=self.target_engine)
        
    def _clean_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """清理数据，处理特殊类型和空值"""
        cleaned = {}
        for key, value in data.items():
            # 跳过主键id字段，让目标数据库自动生成
            if key == 'id':
                continue
            # 处理datetime对象，确保有时区信息
            if isinstance(value, datetime) and value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            # 处理None值，确保与目标表的nullable约束匹配
            cleaned[key] = value
        return cleaned
    
    def migrate_table(self, table_name: str) -> Dict[str, int]:
        """迁移指定表的数据"""
        result = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'failed_records': []
        }
        
        logger.info(f"开始迁移表 {table_name} 的数据...")
        
        try:
            # 获取源表数据
            with self.SourceSession() as source_session:
                result['total'] = source_session.execute(
                    text(f"SELECT COUNT(*) FROM {table_name}")
                ).scalar()
                logger.info(f"源表 {table_name} 共有 {result['total']} 条记录")
                
                # 分批查询数据，每批1000条
                batch_size = 1000
                offset = 0
                
                while offset < result['total']:
                    rows = source_session.execute(
                        text(f"SELECT * FROM {table_name} LIMIT {batch_size} OFFSET {offset}")
                    ).all()
                    
                    if not rows:
                        break
                    
                    # 迁移当前批次数据
                    with self.TargetSession() as target_session:
                        try:
                            for row in rows:
                                # 将Row对象转换为字典
                                row_dict = dict(row._mapping)
                                cleaned_data = self._clean_data(row_dict)
                                
                                # 构建插入语句
                                columns = ', '.join(cleaned_data.keys())
                                placeholders = ', '.join([f':{key}' for key in cleaned_data.keys()])
                                insert_sql = text(
                                    f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
                                )
                                
                                try:
                                    # 执行插入
                                    target_session.execute(insert_sql, cleaned_data)
                                    result['success'] += 1
                                except IntegrityError as e:
                                    # 处理唯一约束冲突
                                    logger.warning(f"记录已存在，跳过: {cleaned_data.get('userid' if table_name == 'users' else 'transaction_id')}")
                                    result['failed'] += 1
                                    result['failed_records'].append(cleaned_data)
                                except Exception as e:
                                    logger.error(f"插入记录失败: {str(e)}")
                                    result['failed'] += 1
                                    result['failed_records'].append(cleaned_data)
                            
                            # 提交事务
                            target_session.commit()
                        except Exception as e:
                            target_session.rollback()
                            logger.error(f"批处理失败: {str(e)}")
                        
                    offset += batch_size
                    logger.info(f"已处理 {min(offset, result['total'])} / {result['total']} 条记录")
            
            logger.info(f"表 {table_name} 数据迁移完成: 总计 {result['total']}, 成功 {result['success']}, 失败 {result['failed']}")
            
        except SQLAlchemyError as e:
            logger.error(f"迁移表 {table_name} 时发生数据库错误: {str(e)}")
            result['failed'] = result['total']
        except Exception as e:
            logger.error(f"迁移表 {table_name} 时发生未知错误: {str(e)}")
            result['failed'] = result['total']
        
        return result
    
    def close(self):
        """关闭数据库连接"""
        self.source_engine.dispose()
        self.target_engine.dispose()


def main():
    """主函数"""
    try:
        # 配置数据库连接信息
        # WSL中的数据库连接URL
        source_db_url = f"postgresql+psycopg://postgres:152183312@localhost:5432/fastapi-ledger"
        
        # 当前Docker环境中的数据库连接URL
        target_db_url = "postgresql+psycopg://postgres:152183312@localhost:5433/fastapi-ledger"
        
        logger.info("开始数据迁移...")
        logger.info(f"源数据库: {source_db_url}")
        logger.info(f"目标数据库: {target_db_url}")
        
        # 创建数据迁移器
        migrator = DataMigrator(source_db_url, target_db_url)
        
        try:
            # 检查源数据库连接
            with migrator.source_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("成功连接到源数据库")
            
            # 检查目标数据库连接
            with migrator.target_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("成功连接到目标数据库")
            
            # 迁移顺序：先迁移users表，再迁移transactions表
            tables_to_migrate = ['users', 'transactions', 'fileassets', 'loggers']
            migration_results = {}
            
            for table in tables_to_migrate:
                migration_results[table] = migrator.migrate_table(table)
            
            # 打印迁移摘要
            logger.info("\n数据迁移摘要:")
            for table, result in migration_results.items():
                logger.info(f"{table}: 总计 {result['total']}, 成功 {result['success']}, 失败 {result['failed']}")
            
            logger.info("\n数据迁移完成！")
            
        finally:
            migrator.close()
            logger.info("数据库连接已关闭")
            
    except Exception as e:
        logger.error(f"数据迁移过程中发生错误: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()