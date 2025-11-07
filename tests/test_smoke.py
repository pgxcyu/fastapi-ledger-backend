import os, requests

BASE = os.getenv("BASE", "http://localhost:9000")

def test_docs_alive():
    r = requests.get(f"{BASE}/docs")
    assert r.status_code == 200
    print("✅ test_docs_alive: Passed")
    return True

def test_health_alive():
    r = requests.get(f"{BASE}/system/healthz")
    assert r.status_code == 200
    # 简化断言，只检查状态码
    print("✅ test_health_alive: Passed")
    return True

# 执行测试
if __name__ == "__main__":
    print("Running smoke tests...")
    try:
        test_docs_alive()
        test_health_alive()
        print("\n🎉 All tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        exit(1)
