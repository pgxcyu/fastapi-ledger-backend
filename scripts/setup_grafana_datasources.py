import requests
import time

# Grafana API配置
GRAFANA_URL = "http://localhost:3000"
GRAFANA_USER = "admin"
GRAFANA_PASSWORD = "admin"

# 等待Grafana完全启动
def wait_for_grafana():
    print("等待Grafana启动...")
    for _ in range(30):
        try:
            response = requests.get(f"{GRAFANA_URL}/api/health", auth=(GRAFANA_USER, GRAFANA_PASSWORD))
            if response.status_code == 200:
                print("Grafana已启动!")
                return True
        except Exception as e:
            pass
        time.sleep(1)
    return False

# 添加Prometheus数据源
def add_prometheus_datasource():
    datasource = {
        "name": "Prometheus",
        "type": "prometheus",
        "url": "http://prometheus:9090",  # 使用服务名称而不是IP
        "access": "proxy",
        "isDefault": True
    }
    
    try:
        response = requests.post(
            f"{GRAFANA_URL}/api/datasources",
            json=datasource,
            auth=(GRAFANA_USER, GRAFANA_PASSWORD)
        )
        
        if response.status_code in [200, 201]:
            print("Prometheus数据源添加成功!")
            return True
        else:
            print(f"Prometheus数据源添加失败: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"添加Prometheus数据源时出错: {str(e)}")
        return False

# 添加Loki数据源
def add_loki_datasource():
    datasource = {
        "name": "Loki",
        "type": "loki",
        "url": "http://loki:3100",  # 使用服务名称而不是IP
        "access": "proxy"
    }
    
    try:
        response = requests.post(
            f"{GRAFANA_URL}/api/datasources",
            json=datasource,
            auth=(GRAFANA_USER, GRAFANA_PASSWORD)
        )
        
        if response.status_code in [200, 201]:
            print("Loki数据源添加成功!")
            return True
        else:
            print(f"Loki数据源添加失败: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"添加Loki数据源时出错: {str(e)}")
        return False

# 检查数据源是否已存在
def check_datasource_exists(name):
    try:
        response = requests.get(
            f"{GRAFANA_URL}/api/datasources",
            auth=(GRAFANA_USER, GRAFANA_PASSWORD)
        )
        
        if response.status_code == 200:
            datasources = response.json()
            for ds in datasources:
                if ds['name'] == name:
                    return True
        return False
    except Exception as e:
        print(f"检查数据源时出错: {str(e)}")
        return False

# 更新数据源
def update_datasource(name, datasource):
    try:
        # 获取数据源ID
        response = requests.get(
            f"{GRAFANA_URL}/api/datasources",
            auth=(GRAFANA_USER, GRAFANA_PASSWORD)
        )
        
        if response.status_code == 200:
            datasources = response.json()
            for ds in datasources:
                if ds['name'] == name:
                    # 更新数据源
                    update_response = requests.put(
                        f"{GRAFANA_URL}/api/datasources/{ds['id']}",
                        json=datasource,
                        auth=(GRAFANA_USER, GRAFANA_PASSWORD)
                    )
                    
                    if update_response.status_code == 200:
                        print(f"{name}数据源更新成功!")
                        return True
                    else:
                        print(f"{name}数据源更新失败: {update_response.status_code} - {update_response.text}")
                        return False
        return False
    except Exception as e:
        print(f"更新数据源时出错: {str(e)}")
        return False

# 主函数
def main():
    if not wait_for_grafana():
        print("Grafana启动超时，无法继续设置数据源")
        return
    
    # 设置Prometheus数据源
    prometheus_ds = {
        "name": "Prometheus",
        "type": "prometheus",
        "url": "http://prometheus:9090",
        "access": "proxy",
        "isDefault": True
    }
    
    if check_datasource_exists("Prometheus"):
        update_datasource("Prometheus", prometheus_ds)
    else:
        add_prometheus_datasource()
    
    # 设置Loki数据源
    loki_ds = {
        "name": "Loki",
        "type": "loki",
        "url": "http://loki:3100",
        "access": "proxy"
    }
    
    if check_datasource_exists("Loki"):
        update_datasource("Loki", loki_ds)
    else:
        add_loki_datasource()

if __name__ == "__main__":
    main()