#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SQLite数据库查看器
用于在没有安装sqlite3命令行工具的Windows系统上查看和管理SQLite数据库
"""

import sqlite3
import argparse
import os
from typing import List, Dict, Any


def list_tables(db_path: str) -> List[str]:
    """列出数据库中的所有表"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()
    return tables


def describe_table(db_path: str, table_name: str) -> List[Dict[str, Any]]:
    """描述表的结构"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name});")
    columns = []
    for row in cursor.fetchall():
        columns.append({
            'cid': row[0],
            'name': row[1],
            'type': row[2],
            'notnull': row[3],
            'dflt_value': row[4],
            'pk': row[5]
        })
    conn.close()
    return columns


def execute_query(db_path: str, query: str) -> List[Dict[str, Any]]:
    """执行SQL查询并返回结果"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # 使结果可以通过列名访问
    cursor = conn.cursor()
    try:
        cursor.execute(query)
        # 如果是SELECT语句或者返回结果的语句
        if query.strip().upper().startswith('SELECT'):
            rows = cursor.fetchall()
            result = []
            for row in rows:
                result.append(dict(row))
            return result
        else:
            # 对于其他语句，提交更改
            conn.commit()
            return [{'affected_rows': cursor.rowcount}]
    except Exception as e:
        conn.rollback()
        return [{'error': str(e)}]
    finally:
        conn.close()


def print_tables(tables: List[str]) -> None:
    """打印表列表"""
    print("\n数据库中的表：")
    if not tables:
        print("  没有找到表")
        return
    for i, table in enumerate(tables, 1):
        print(f"  {i}. {table}")


def print_table_structure(columns: List[Dict[str, Any]]) -> None:
    """打印表结构"""
    print("\n表结构：")
    if not columns:
        print("  表结构信息不可用")
        return
    print("  列名              类型                是否为空  默认值  主键")
    print("  " + "-" * 60)
    for col in columns:
        print(f"  {col['name']:<18} {col['type']:<20} {'' if col['notnull'] else 'NOT NULL':<8} {str(col['dflt_value'] if col['dflt_value'] is not None else ''):<6} {'' if col['pk'] else 'PRIMARY KEY':<10}")


def print_query_results(results: List[Dict[str, Any]]) -> None:
    """打印查询结果"""
    if not results:
        print("\n查询结果为空")
        return

    # 检查是否有错误
    if 'error' in results[0]:
        print(f"\n查询错误: {results[0]['error']}")
        return

    # 检查是否是受影响的行数
    if 'affected_rows' in results[0]:
        print(f"\n操作成功，影响了 {results[0]['affected_rows']} 行")
        return

    # 打印结果标题
    headers = results[0].keys()
    print("\n查询结果：")
    print("  " + " | ".join(f"{h:<15}" for h in headers))
    print("  " + "-" * (17 * len(headers) - 3))
    
    # 打印结果行
    for row in results:
        print("  " + " | ".join(f"{str(row[h])[:15]:<15}" for h in headers))


def interactive_shell(db_path: str) -> None:
    """交互式shell模式"""
    print(f"\n=== SQLite数据库交互工具 ===")
    print(f"已连接到数据库: {db_path}")
    print("可用命令:")
    print("  .tables          - 查看所有表")
    print("  .desc <表名>     - 查看表结构")
    print("  .exit 或 .quit   - 退出工具")
    print("  SQL语句          - 执行SQL查询")
    print("==========================")
    
    while True:
        try:
            cmd = input("\nsqlite> ").strip()
            if not cmd:
                continue
            
            if cmd.lower() in ('.exit', '.quit', 'exit', 'quit'):
                print("退出工具。")
                break
            elif cmd.lower() == '.tables':
                tables = list_tables(db_path)
                print_tables(tables)
            elif cmd.lower().startswith('.desc '):
                _, table_name = cmd.split(' ', 1)
                columns = describe_table(db_path, table_name)
                print_table_structure(columns)
            else:
                # 尝试作为SQL执行
                results = execute_query(db_path, cmd)
                print_query_results(results)
        except KeyboardInterrupt:
            print("\n退出工具。")
            break
        except Exception as e:
            print(f"错误: {e}")


def main():
    parser = argparse.ArgumentParser(description='SQLite数据库查看器')
    parser.add_argument('db_path', default='database.db', nargs='?', help='SQLite数据库文件路径')
    parser.add_argument('--tables', action='store_true', help='列出数据库中的所有表')
    parser.add_argument('--desc', help='查看指定表的结构')
    parser.add_argument('--query', help='执行SQL查询')
    
    args = parser.parse_args()
    
    # 检查数据库文件是否存在
    if not os.path.exists(args.db_path):
        print(f"错误：数据库文件 '{args.db_path}' 不存在")
        return
    
    # 根据命令行参数执行相应操作
    if args.tables:
        tables = list_tables(args.db_path)
        print_tables(tables)
    elif args.desc:
        columns = describe_table(args.db_path, args.desc)
        print_table_structure(columns)
    elif args.query:
        results = execute_query(args.db_path, args.query)
        print_query_results(results)
    else:
        # 默认进入交互式shell
        interactive_shell(args.db_path)


if __name__ == '__main__':
    main()