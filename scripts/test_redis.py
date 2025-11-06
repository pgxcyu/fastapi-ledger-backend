import redis
import time

def test_redis_connection():
    print("测试Redis连接...")
    try:
        # 尝试连接到本地Redis
        r = redis.Redis(host='localhost', port=6379, db=0, socket_connect_timeout=5)
        start_time = time.time()
        response = r.ping()
        end_time = time.time()
        print(f"✅ Redis连接成功! 响应时间: {(end_time - start_time)*1000:.2f}ms")
        print(f"响应: {response}")
        
        # 测试基本操作
        r.set('test_key', 'Hello Redis!')
        value = r.get('test_key')
        print(f"✅ 设置和获取操作成功: {value.decode()}")
        
        # 清理测试数据
        r.delete('test_key')
        print("✅ 清理测试数据成功")
        
        return True
    except Exception as e:
        print(f"❌ Redis连接失败: {str(e)}")
        
        # 尝试用不同的主机地址
        try:
            print("\n尝试使用127.0.0.1连接...")
            r = redis.Redis(host='127.0.0.1', port=6379, db=0, socket_connect_timeout=5)
            response = r.ping()
            print(f"✅ 使用127.0.0.1连接成功!")
            return True
        except Exception as e2:
            print(f"❌ 使用127.0.0.1连接也失败: {str(e2)}")
        
        # 检查端口是否被占用
        print("\n检查6379端口是否被占用...")
        import subprocess
        try:
            if subprocess.run(["netstat", "-ano"], shell=True).returncode == 0:
                print("请手动检查6379端口是否在运行")
        except:
            print("无法检查端口占用情况")
        
        return False

if __name__ == "__main__":
    success = test_redis_connection()
    print(f"\n测试结果: {'成功' if success else '失败'}")