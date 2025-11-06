import os
import sys

# Add project root to path
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, base_dir)

def test_task_registration():
    """测试Celery任务注册是否成功"""
    print("测试Celery任务注册...")
    
    try:
        # 导入Celery应用实例
        from app.core.celery_config import celery_app
        
        # 打印所有已注册的任务
        print("\n已注册的Celery任务:")
        print("-" * 50)
        tasks = celery_app.tasks
        
        # 筛选出应用的任务（排除Celery内置任务）
        app_tasks = {name: task for name, task in tasks.items() if not name.startswith('celery.')}
        
        if not app_tasks:
            print("未找到任何应用任务！")
        else:
            for name, task in app_tasks.items():
                print(f"任务名称: {name}")
                print(f"  模块: {task.__module__}")
                print(f"  函数: {task.__name__}")
                print(f"  类型: {type(task)}")
                print()
        
        # 特别检查我们关注的任务是否存在
        target_task = 'app.tasks.celery_tasks.export_transactions_by_user_task'
        if target_task in tasks:
            print(f"✓ 成功找到任务: {target_task}")
            print("任务注册问题已解决！")
            return True
        else:
            print(f"✗ 未找到任务: {target_task}")
            print("任务注册问题仍然存在。")
            return False
            
    except ImportError as e:
        print(f"导入错误: {e}")
        return False
    except Exception as e:
        print(f"测试过程中出错: {e}")
        return False

if __name__ == "__main__":
    success = test_task_registration()
    sys.exit(0 if success else 1)