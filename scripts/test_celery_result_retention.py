#!/usr/bin/env python3
# 测试Celery任务结果保留时间配置

import time
from app.core.celery_config import celery_app
from app.tasks.celery_tasks import cleanup_files_task
import redis
import os

print("开始测试Celery任务结果保留配置...")

# 获取Redis连接参数
redis_url = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/2")
print(f"使用的Redis结果后端: {redis_url}")

# 解析Redis URL
if redis_url.startswith("redis://"):
    # 简单解析redis://redis:6379/2格式
    parts = redis_url[8:].split(":")
    host = parts[0]
    port_db = parts[1].split("/")
    port = int(port_db[0])
    db = int(port_db[1])
else:
    # 默认值
    host = "redis"
    port = 6379
    db = 2

# 创建Redis连接
redis_client = redis.Redis(host=host, port=port, db=db, decode_responses=True)
print(f"已连接到Redis: {host}:{port} DB:{db}")

# 清除当前数据库中的所有键（仅用于测试）
print("清除测试前的Redis数据...")
redis_client.flushdb()
print(f"测试前的键数量: {len(redis_client.keys('*'))}")

# 发送任务
print("发送测试任务...")
task = cleanup_files_task.delay(dry_run=True)
task_id = task.id
print(f"任务ID: {task_id}")

# 等待任务完成
print("等待任务完成...")
task.wait(timeout=10)
print(f"任务状态: {task.status}")

# 检查Redis中是否有任务结果
print("\n检查Redis中的任务结果...")
keys = redis_client.keys('*')
print(f"测试后的键数量: {len(keys)}")
if keys:
    print("Redis中的键:")
    for key in keys:
        print(f"  - {key}")
        # 尝试获取键的值类型
        key_type = redis_client.type(key)
        print(f"    类型: {key_type}")
        
        # 对于字符串类型，显示部分内容
        if key_type == 'string' and len(key) > 10:
            try:
                value = redis_client.get(key)
                if value:
                    print(f"    值预览: {value[:100]}...")
            except Exception as e:
                print(f"    无法读取值: {e}")
else:
    print("警告: Redis中没有找到任务结果键！")

# 尝试直接获取任务结果
print("\n直接获取任务结果:")
try:
    result = task.result
    print(f"任务结果: {result}")
except Exception as e:
    print(f"获取任务结果时出错: {e}")

print("\n测试完成！任务结果应该会在Redis中保留7天（根据配置）。")