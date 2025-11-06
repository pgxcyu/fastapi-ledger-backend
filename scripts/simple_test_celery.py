import os
import sys

# Add project root to path
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, base_dir)

# Import Celery app
from app.core.celery_config import celery_app

print("\n测试Celery任务注册:")
print("-" * 50)

# Get all registered tasks
tasks = celery_app.tasks

# Filter out built-in tasks
app_tasks = {name: task for name, task in tasks.items() if not name.startswith('celery.')}

print(f"找到 {len(app_tasks)} 个应用任务:\n")
for name, task in app_tasks.items():
    print(f"✓ 任务名称: {name}")

# Check specific task
target_task = 'app.tasks.celery_tasks.export_transactions_by_user_task'
if target_task in tasks:
    print(f"\n🎉 成功找到目标任务: {target_task}")
else:
    print(f"\n❌ 未找到目标任务: {target_task}")