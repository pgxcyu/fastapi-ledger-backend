import os
import sys
import requests

# 确保能导入项目模块
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# 仅在pytest环境中尝试导入client，避免直接运行时导入app.main
try:
    # 检查是否在pytest环境中运行
    if "pytest" in sys.modules:
        from fastapi.testclient import TestClient
        from app.main import app
        client = TestClient(app)
    else:
        client = None
except ImportError:
    client = None

# 用于直接运行时的配置
BASE = os.getenv("BASE", "http://localhost:9000")

def test_docs_alive():
    # 根据是否在pytest环境中选择测试方式
    if client is not None:
        # 在pytest环境中使用TestClient
        r = client.get("/docs")
    else:
        # 直接运行时使用requests
        r = requests.get(f"{BASE}/docs")
    assert r.status_code == 200

def test_health_alive():
    # 根据是否在pytest环境中选择测试方式
    if client is not None:
        # 在pytest环境中使用TestClient
        r = client.get("/system/healthz")
    else:
        # 直接运行时使用requests
        r = requests.get(f"{BASE}/system/healthz")
    assert r.status_code == 200

# 执行测试
if __name__ == "__main__":
    print("Running smoke tests...")
    try:
        test_docs_alive()
        print("✅ test_docs_alive: Passed")
        
        test_health_alive()
        print("✅ test_health_alive: Passed")
        
        print("\n🎉 All tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        exit(1)
