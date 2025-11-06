import sys
sys.path.append('.')
import logging
from loguru import logger

# 直接配置日志，确保日志写入文件
from app.core.logging import setup_logging

# 确保日志配置被初始化
setup_logging()

# 测试应用日志
logger.info("This is a test app log")
logger.error("This is a test error log")

# 测试带上下文的日志
logger.bind(request_id="test-123", user_id="user-456", sid="session-789").info("Test with context")

print("Logging test completed")