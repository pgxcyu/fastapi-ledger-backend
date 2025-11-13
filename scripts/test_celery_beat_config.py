#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试Celery Beat配置脚本

用于验证Celery Beat配置是否正确工作，特别是cron表达式解析功能。
"""

import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.celery_config import crontab_from_string, celery_app
from app.core.config import settings

def test_crontab_parsing():
    """测试cron表达式解析功能"""
    print("===== 测试cron表达式解析 =====")
    try:
        # 测试默认的清理任务cron表达式
        cron_string = settings.CLEANUP_CRON
        print(f"测试cron表达式: {cron_string}")
        crontab_obj = crontab_from_string(cron_string)
        print(f"解析结果: minute={crontab_obj.minute}, hour={crontab_obj.hour}, day={crontab_obj.day_of_month}, month={crontab_obj.month_of_year}, weekday={crontab_obj.day_of_week}")
        print("✓ cron表达式解析成功")
        return True
    except Exception as e:
        print(f"✗ cron表达式解析失败: {e}")
        return False

def test_celery_beat_schedule():
    """测试Celery Beat调度配置"""
    print("\n===== 测试Celery Beat调度配置 =====")
    try:
        # 获取beat调度配置
        beat_schedule = celery_app.conf.beat_schedule
        print(f"Beat调度配置: {beat_schedule}")
        
        # 检查清理任务是否已配置
        if 'cleanup-files-daily' in beat_schedule:
            task_config = beat_schedule['cleanup-files-daily']
            print(f"清理任务配置: {task_config}")
            print(f"任务ID: {task_config['task']}")
            print(f"任务参数: {task_config['args']}")
            print("✓ 清理任务已正确配置")
            return True
        else:
            print("✗ 清理任务未配置")
            return False
    except Exception as e:
        print(f"✗ Celery Beat配置检查失败: {e}")
        return False

def main():
    """运行所有测试"""
    print("开始测试Celery Beat配置...")
    
    tests = [
        test_crontab_parsing,
        test_celery_beat_schedule
    ]
    
    all_passed = True
    for test in tests:
        if not test():
            all_passed = False
    
    print("\n===== 测试结果 =====")
    if all_passed:
        print("🎉 所有测试通过！Celery Beat配置正确。")
        return 0
    else:
        print("❌ 测试失败，请检查配置。")
        return 1

if __name__ == "__main__":
    sys.exit(main())