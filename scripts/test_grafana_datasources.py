import requests

# Grafana API配置
GRAFANA_URL = "http://localhost:3000"
GRAFANA_USER = "admin"
GRAFANA_PASSWORD = "admin"

# 测试数据源健康状态
def test_datasource_health(name):
    try:
        # 获取数据源信息
        response = requests.get(
            f"{GRAFANA_URL}/api/datasources",
            auth=(GRAFANA_USER, GRAFANA_PASSWORD)
        )
        
        if response.status_code != 200:
            print(f"获取数据源列表失败: {response.status_code} - {response.text}")
            return False
        
        datasources = response.json()
        datasource_uid = None
        
        for ds in datasources:
            if ds['name'] == name:
                datasource_uid = ds['uid']
                break
        
        if not datasource_uid:
            print(f"未找到数据源: {name}")
            return False
        
        # 测试数据源健康状态
        health_response = requests.get(
            f"{GRAFANA_URL}/api/datasources/uid/{datasource_uid}/health",
            auth=(GRAFANA_USER, GRAFANA_PASSWORD)
        )
        
        if health_response.status_code == 200:
            health_data = health_response.json()
            print(f"{name} 数据源健康状态: 正常")
            print(f"  状态: {health_data.get('status', '未知')}")
            print(f"  详情: {health_data.get('message', '无')}")
            return True
        else:
            print(f"{name} 数据源健康检查失败: {health_response.status_code} - {health_response.text}")
            return False
            
    except Exception as e:
        print(f"测试{name}数据源时出错: {str(e)}")
        return False

# 测试Prometheus查询
def test_prometheus_query():
    try:
        # 简单的Prometheus查询
        query = "up"
        response = requests.get(
            f"{GRAFANA_URL}/api/datasources/proxy/1/api/v1/query?query={query}",
            auth=(GRAFANA_USER, GRAFANA_PASSWORD)
        )
        
        if response.status_code == 200:
            data = response.json()
            print("\nPrometheus 查询测试成功!")
            if 'data' in data and 'result' in data['data']:
                print(f"查询结果数量: {len(data['data']['result'])}")
                for result in data['data']['result'][:3]:  # 只显示前3个结果
                    print(f"  - {result['metric']} = {result['value'][1]}")
            return True
        else:
            print(f"Prometheus查询失败: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"测试Prometheus查询时出错: {str(e)}")
        return False

# 测试Loki查询
def test_loki_query():
    try:
        # 简单的Loki查询
        query = "{job=\"promtail\"}"
        response = requests.get(
            f"{GRAFANA_URL}/api/datasources/proxy/2/loki/api/v1/query_range?query={query}&limit=10",
            auth=(GRAFANA_USER, GRAFANA_PASSWORD)
        )
        
        if response.status_code == 200:
            data = response.json()
            print("\nLoki 查询测试成功!")
            if 'data' in data and 'result' in data['data']:
                print(f"查询结果流数量: {len(data['data']['result'])}")
                for result in data['data']['result'][:2]:  # 只显示前2个流
                    print(f"  流: {result['stream']}")
                    print(f"  日志条目数: {len(result['values'])}")
                    if result['values']:
                        print(f"  最新日志: {result['values'][-1][1]}")
            return True
        else:
            print(f"Loki查询失败: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"测试Loki查询时出错: {str(e)}")
        return False

# 主函数
def main():
    print("===== Grafana 数据源测试 =====")
    
    # 测试Prometheus数据源
    print("\n1. 测试 Prometheus 数据源:")
    prometheus_healthy = test_datasource_health("Prometheus")
    
    # 测试Loki数据源
    print("\n2. 测试 Loki 数据源:")
    loki_healthy = test_datasource_health("Loki")
    
    # 如果数据源健康，进行查询测试
    if prometheus_healthy:
        test_prometheus_query()
    
    if loki_healthy:
        test_loki_query()
    
    print("\n===== 测试完成 =====")
    print(f"Prometheus数据源状态: {'✓ 正常' if prometheus_healthy else '✗ 异常'}")
    print(f"Loki数据源状态: {'✓ 正常' if loki_healthy else '✗ 异常'}")

if __name__ == "__main__":
    main()