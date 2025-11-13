# 监控与日志系统配置指南

本文档详细介绍了项目中配置的监控（Prometheus + Grafana）和日志收集（Loki + Promtail）系统的使用方法。

## 已配置的服务

通过 `docker-compose.yml`，我们已配置了以下服务：

| 服务 | 容器名 | 端口 | 说明 |
|------|--------|------|------|
| Prometheus | prometheus | 9090 | 指标收集和存储 |
| Grafana | grafana | 3000 | 可视化面板 |
| Loki | loki | 3100 | 日志存储 |
| Promtail | promtail | 9080 | 日志采集器 |

## 访问服务

启动所有服务后，可以通过以下地址访问：

- Prometheus UI: http://localhost:9090
- Grafana UI: http://localhost:3000
- Loki API: http://localhost:3100

## Grafana 配置

### 1. 登录 Grafana

- 访问 http://localhost:3000
- 默认用户名: `admin`
- 默认密码: `admin`（首次登录会要求修改密码）

### 2. 添加 Prometheus 数据源

1. 登录后，点击左侧菜单的 "Configuration" → "Data sources"
2. 点击 "Add data source"
3. 选择 "Prometheus"
4. 配置以下参数：
   - Name: `Prometheus`
   - URL: `http://prometheus:9090`
   - 其余保持默认设置
5. 点击 "Save & Test" 确认连接成功

### 3. 添加 Loki 数据源

1. 点击左侧菜单的 "Configuration" → "Data sources"
2. 点击 "Add data source"
3. 选择 "Loki"
4. 配置以下参数：
   - Name: `Loki`
   - URL: `http://loki:3100`
   - 其余保持默认设置
5. 点击 "Save & Test" 确认连接成功

## 查看指标

### 在 Prometheus 中

1. 访问 http://localhost:9090
2. 在顶部的搜索框中，可以输入以下常用指标：
   - `http_requests_total`: 请求总数
   - `http_request_duration_seconds`: 请求延迟
   - `fastapi_requests_inprogress`: 当前活跃请求数

### 在 Grafana 中创建 Prometheus 仪表板

1. 点击左侧菜单的 "+" → "Create" → "Dashboard"
2. 点击 "Add a new panel"
3. 在查询编辑器中，选择 "Prometheus" 数据源
4. 输入查询语句，例如：
   ```
   sum(rate(http_requests_total[5m])) by (status_code, method)
   ```
5. 配置图表标题、图例等
6. 点击右上角的 "Save" 保存仪表板

## 查看日志

### 在 Grafana 中查看 Loki 日志

1. 点击左侧菜单的 "+" → "Explore"
2. 选择 "Loki" 数据源
3. 在日志浏览器中，可以通过以下方式过滤日志：
   - 按标签过滤：`{job="fastapi-app-logs"}`
   - 按日志级别过滤：`{job="fastapi-app-logs", level="ERROR"}`
   - 按关键词搜索：在搜索框中输入关键词

### 日志查询示例

1. 查看所有错误日志：
   ```
   {job="fastapi-app-logs", level="ERROR"}
   ```

2. 查看包含特定请求 ID 的日志：
   ```
   {job="fastapi-app-logs"} |= "request_id=xxx-xxx-xxx"
   ```

3. 查看特定模块的日志：
   ```
   {job="fastapi-app-logs", module="app.core.celery_config"}
   ```

## 自定义指标（可选）

如果需要添加更多自定义指标，可以在 `app/main.py` 文件中的 `setup_prometheus` 函数中扩展：

```python
from prometheus_client import Counter, Histogram

# 定义自定义计数器
custom_counter = Counter("my_custom_counter", "Custom counter for business logic")

# 定义自定义延迟指标
custom_histogram = Histogram("my_custom_duration_seconds", "Duration of custom operation")

def setup_prometheus():
    # 现有配置...
    
    # 在需要的地方使用自定义指标
    # custom_counter.inc()
    # with custom_histogram.time():
    #     # 执行操作
```

## 故障排除

### 无法访问 /metrics 端点

1. 确认 FastAPI 应用已启动
2. 检查 `app/main.py` 中的 `setup_prometheus()` 函数是否正确配置
3. 查看应用日志是否有错误信息

### Promtail 无法收集日志

1. 确认 `logs` 卷已正确挂载到 Promtail 容器
2. 检查 `promtail-config.yml` 中的配置是否正确
3. 查看 Promtail 容器日志：`docker logs promtail`

### Grafana 无法连接数据源

1. 确认 Prometheus 和 Loki 服务已正常运行
2. 检查数据源 URL 是否正确（使用容器名称作为主机名）
3. 查看 Grafana 容器日志：`docker logs grafana`

## 最佳实践

1. **定期清理数据**：监控和日志数据会占用存储空间，建议配置适当的数据保留策略
2. **设置告警**：可以在 Prometheus 中配置告警规则，当指标超过阈值时通知
3. **优化查询**：避免在 Grafana 中使用过于复杂的查询，以免影响性能
4. **保护访问**：生产环境中，建议为监控服务配置访问控制

---

通过以上配置，您的 FastAPI 应用已成功集成了完整的监控和日志收集系统，可以实时监控应用性能和分析日志数据。