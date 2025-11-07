# Prometheus FastAPI 监控指南

本文档详细介绍如何在 FastAPI 项目中使用 `prometheus-fastapi-instrumentator` 进行性能监控和指标收集。

## 什么是 prometheus-fastapi-instrumentator

`prometheus-fastapi-instrumentator` 是一个用于 FastAPI 应用的 Prometheus 指标收集器，可以自动收集以下指标：

- 请求数量（按状态码分类）
- 请求延迟（平均值、最大值等）
- 活跃请求数
- 应用内存使用情况

## 安装

确保 `requirements.txt` 中包含以下依赖：

```bash
# 在 requirements.txt 中添加
prometheus-fastapi-instrumentator
```

## 基本使用方法

### 1. 在 main.py 中导入并初始化

```python
# 在 app/main.py 中导入
from prometheus_fastapi_instrumentator import Instrumentator

# 在 FastAPI 应用创建后
def setup_prometheus():
    # 创建并配置 Instrumentator
    instrumentator = Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        should_respect_env_var=True,
        should_instrument_requests_inprogress=True,
        excluded_handlers=["/metrics"],  # 避免监控自身
        env_var_name="ENABLE_METRICS",
        inprogress_name="fastapi_requests_inprogress",
        inprogress_labels=True
    )
    
    # 为应用添加指标收集
    instrumentator.instrument(app)
    
    # 暴露 /metrics 端点，供 Prometheus 抓取
    instrumentator.expose(app, endpoint="/metrics", include_in_schema=False)

# 在启动事件中调用
@app.on_event("startup")
async def startup_event():
    init_db()
    # ... 其他初始化代码 ...
    setup_prometheus()  # 添加这一行
```

### 2. 集成到现有的 main.py

将上面的设置添加到您现有的 `app/main.py` 文件中：

```python
# 在导入部分添加
from prometheus_fastapi_instrumentator import Instrumentator

# 在 startup_event 函数中添加
@app.on_event("startup")
async def startup_event():
    init_db()
    
    # 设置 Prometheus 监控
    Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
    
    # ... 其他现有代码 ...
```

## 高级配置选项

### 1. 自定义指标

您可以添加自定义指标来监控特定业务逻辑：

```python
from prometheus_fastapi_instrumentator import Instrumentator, metrics
from prometheus_client import Counter

# 定义自定义计数器
custom_counter = Counter("my_custom_counter", "Custom counter for business logic")

# 在处理函数中使用
@app.get("/some-endpoint")
async def some_endpoint():
    custom_counter.inc()
    return {"message": "Hello World"}

# 配置 Instrumentator
def setup_prometheus():
    instrumentator = Instrumentator()
    
    # 添加默认指标
    instrumentator.instrument(app)
    
    # 添加自定义指标
    instrumentator.add(
        metrics.Info(
            name="app_info",
            description="Application information",
            labels={"version": "1.0.0"}
        )
    )
    
    instrumentator.expose(app)
```

### 2. 指标过滤和分组

```python
instrumentator = Instrumentator(
    # 按状态码分组（2xx, 3xx, 4xx, 5xx）
    should_group_status_codes=True,
    
    # 忽略未模板化的路由（如 /items/123）
    should_ignore_untemplated=True,
    
    # 排除某些路由
    excluded_handlers=["/health", "/docs", "/redoc"]
)
```

### 3. 自定义延迟指标

```python
from prometheus_fastapi_instrumentator import metrics

instrumentator = Instrumentator()

# 添加自定义延迟指标
instrumentator.add(
    metrics.request_size(
        should_include_handler=True,
        should_include_method=True,
        should_include_status=True,
        metric_namespace="custom",
        metric_subsystem="http"
    )
)

instrumentator.add(
    metrics.response_size(
        should_include_handler=True,
        should_include_method=True,
        should_include_status=True,
        metric_namespace="custom",
        metric_subsystem="http"
    )
)

instrumentator.instrument(app).expose(app)
```

## 查看和使用指标

### 1. 访问指标端点

启动应用后，可以通过以下 URL 访问收集的指标：

```
http://localhost:9000/metrics
```

### 2. 配置 Prometheus 抓取

在 Prometheus 配置文件中添加以下内容，使其定期抓取您的指标：

```yaml
scrape_configs:
  - job_name: 'fastapi-app'
    scrape_interval: 15s
    static_configs:
      - targets: ['fastapi-ledger-api:9000']
```

### 3. 使用 Grafana 可视化

将 Prometheus 作为数据源添加到 Grafana，然后创建仪表板来可视化以下指标：

- `http_requests_total` - 请求总数（按状态码、方法、路径分类）
- `http_request_duration_seconds` - 请求延迟分布
- `fastapi_requests_inprogress` - 当前活跃请求数

## 示例：完整的集成方案

以下是一个完整的集成示例，包含在 Docker Compose 环境中：

### 1. 更新 main.py

```python
# app/main.py
from prometheus_fastapi_instrumentator import Instrumentator

# 在应用创建后
app = FastAPI(title="FastAPI Ledger")

@app.on_event("startup")
async def startup_event():
    init_db()
    
    # 初始化 Prometheus 监控
    Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=False,
        should_instrument_requests_inprogress=True,
        excluded_handlers=["/metrics", "/healthz", "/readyz"]
    ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
    
    # ... 其他初始化代码 ...
```

### 2. 更新 docker-compose.yml

添加 Prometheus 和 Grafana 服务：

```yaml
# 在 docker-compose.yml 中添加
services:
  # ... 现有服务 ...
  
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"
    depends_on:
      - api
    restart: always
  
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    depends_on:
      - prometheus
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    restart: always
```

### 3. 创建 Prometheus 配置文件

在项目根目录创建 `prometheus.yml`：

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'fastapi-app'
    static_configs:
      - targets: ['fastapi-ledger-api:9000']
  
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
```

## 最佳实践

1. **只收集必要的指标** - 避免过多的标签和不必要的指标，以免增加系统负担
2. **定期清理旧数据** - 配置适当的数据保留策略
3. **设置告警规则** - 基于收集的指标设置关键性能指标的告警
4. **安全访问控制** - 生产环境中确保 `/metrics` 端点受到适当保护
5. **监控端点排除** - 始终将监控自身的端点排除在监控范围之外

## 故障排除

### 常见问题

1. **指标端点无法访问**
   - 检查是否正确调用了 `expose()` 方法
   - 确认端点路径没有冲突

2. **指标收集不完整**
   - 验证 `should_group_status_codes` 和 `should_ignore_untemplated` 设置
   - 检查是否有路由被错误排除

3. **性能影响**
   - 如果监控导致明显性能下降，可以减少采样率或移除某些指标
   - 考虑只在生产环境中启用必要的指标

## 更多资源

- [prometheus-fastapi-instrumentator GitHub 文档](https://github.com/trallnag/prometheus-fastapi-instrumentator)
- [Prometheus 官方文档](https://prometheus.io/docs/)
- [Grafana 官方文档](https://grafana.com/docs/grafana/latest/)