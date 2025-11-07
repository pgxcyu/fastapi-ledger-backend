#!/usr/bin/env python3
# 模拟CI环境测试脚本 - 用于验证PYTHONPATH设置是否能解决模块导入问题

import os
import sys

# 打印当前环境信息
print("当前工作目录:", os.getcwd())
print("当前Python路径:", sys.path)

# 尝试导入之前在CI中失败的模块
print("\n尝试导入app模块...")
try:
    # 直接导入之前失败的模块组合
    from app.core.celery_config import celery_app
    from app.tasks.celery_tasks import cleanup_files_task
    print("✅ 模块导入成功！")
    print(f"成功导入: celery_app={celery_app}")
    print(f"成功导入: cleanup_files_task={cleanup_files_task}")
except ImportError as e:
    print(f"❌ 模块导入失败: {e}")
    print("请确保PYTHONPATH设置正确")

print("\n测试完成！")