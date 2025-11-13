import requests
import sys

# 测试Prometheus API访问
try:
    response = requests.get("http://localhost:9090/api/v1/query", params={"query": "up"})
    print(f"Response status code: {response.status_code}")
    print(f"Response content: {response.text}")
except Exception as e:
    print(f"Error accessing Prometheus API: {e}")
    import traceback
    traceback.print_exc()
sys.exit(0)