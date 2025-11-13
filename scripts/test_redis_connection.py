import redis
import sys

def test_redis_connection(host='localhost', port=6380, db=0):
    """测试Redis连接"""
    try:
        # 创建Redis连接
        r = redis.Redis(host=host, port=port, db=db, decode_responses=True)
        
        # 测试连接
        response = r.ping()
        print(f"Redis连接成功! 响应: {response}")
        
        # 测试简单操作
        r.set('test_key', 'test_value')
        value = r.get('test_key')
        print(f"设置和获取键成功: {value}")
        
        return True
    except Exception as e:
        print(f"Redis连接失败: {e}")
        return False

if __name__ == "__main__":
    success = test_redis_connection()
    sys.exit(0 if success else 1)