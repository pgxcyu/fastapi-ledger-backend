# Celery Beat 配置说明

本文档说明如何使用 Celery Beat 替代原来的 APScheduler 来管理定时任务，并详细介绍日志持久化配置。

## 背景

项目原使用 APScheduler 进行定时任务管理，现已迁移到 Celery Beat，以实现更好的任务调度和管理能力，同时与现有的 Celery 任务队列保持一致。

## 已完成的迁移工作

1. 在 `app/core/celery_config.py` 中添加了 Celery Beat 配置
2. 配置了每日文件清理任务，使用与原 APScheduler 相同的 cron 表达式
3. 移除了 `app/main.py` 中的 APScheduler 相关代码
4. 增强了日志持久化配置，确保 Celery Beat 日志能够统一管理

## 启动 Celery Beat

### 基本启动命令

```bash
celery -A app.core.celery_config beat --loglevel=info
```

### 在开发环境中启动

```bash
# 启动 Celery worker
celery -A app.core.celery_config worker --loglevel=info -P eventlet

# 启动 Celery beat（在另一个终端）
celery -A app.core.celery_config beat --loglevel=info
```

### 同时启动 Worker 和 Beat

也可以在一个命令中同时启动 worker 和 beat，但这仅推荐在开发环境中使用：

```bash
celery -A app.core.celery_config worker --loglevel=info -P eventlet -B
```

## Docker 部署说明

在生产环境中，建议在 Docker Compose 中添加专门的 Celery Beat 服务。示例配置：

```yaml
celery-beat:
  build: .
  command: celery -A app.core.celery_config beat --loglevel=info
  environment:
    - CELERY_BROKER_URL=redis://redis:6379/1
    - CELERY_RESULT_BACKEND=redis://redis:6379/2
    - REDIS_URL=redis://redis:6379/0
    - CLEANUP_CRON=30 3 * * *
  depends_on:
    - redis
  restart: always
```

## 监控 Celery Beat

可以结合 Flower 来监控 Celery Beat 任务执行情况：

```bash
celery -A app.core.celery_config flower
```

然后访问 http://localhost:5555 查看任务执行情况。

## 任务配置

当前配置了以下定时任务：

| 任务名称 | 任务ID | 执行频率 | 说明 |
|---------|--------|----------|------|
| cleanup-files-daily | app.tasks.celery_tasks.cleanup_files_task | 每天 03:30 | 清理孤立文件 |

执行频率由环境变量 `CLEANUP_CRON` 控制，默认值为 `30 3 * * *`（每天凌晨 3:30）。

## 日志持久化配置

### 日志存储位置

项目已配置 Celery Beat 日志持久化到统一的日志目录中：

- **Celery Beat 日志**：存储在 `LOG_DIR/celery-beat.log`
- **Celery Worker 日志**：存储在 `LOG_DIR/celery-worker.log`
- **应用综合日志**：存储在 `LOG_DIR/app.log`
- **错误日志**：存储在 `LOG_DIR/error.log`

默认情况下，`LOG_DIR` 为项目根目录下的 `logs` 文件夹。可以通过环境变量 `LOG_DIR` 自定义日志目录。

### 日志级别配置

Celery 日志级别与项目全局日志级别保持一致，可通过环境变量 `LOG_LEVEL` 配置：

- 默认值：`INFO`
- 可选值：`TRACE`, `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

### 日志轮转与保留

日志配置了自动轮转和保留策略：

- **轮转时间**：每天 0 点自动创建新日志文件
- **保留期限**：日志文件保留 7 天
- **存储格式**：JSON 格式，便于日志采集和分析

### 查看日志的方法

1. **直接查看日志文件**：
   ```bash
   # 查看 Celery Beat 日志
   tail -f logs/celery-beat.log
   
   # 查看应用综合日志（包含所有组件的日志）
   tail -f logs/app.log
   ```

2. **Docker 环境中查看**：
   ```bash
   # 查看 Celery Beat 容器日志
   docker logs -f <celery-beat-container-id>
   
   # 或使用 Docker Compose
   docker compose logs -f celery-beat
   ```

### 日志格式

Celery Beat 日志格式示例：
```
2024-01-01 12:00:00,000 - INFO - [MainProcess:12345] beat: Starting...
2024-01-01 12:00:00,100 - INFO - [MainProcess:12345] beat: Scheduler: Sending due task cleanup-files-daily (app.tasks.celery_tasks.cleanup_files_task)
```

## 注意事项

1. 确保 Redis 服务正常运行，Celery Beat 需要使用 Redis 作为消息代理
2. Celery Beat 会在当前目录生成 `celerybeat-schedule.db` 文件，用于记录任务执行历史
3. 如需修改任务执行频率，只需修改环境变量 `CLEANUP_CRON` 即可
4. 在生产环境中，日志文件可能会占用大量磁盘空间，建议定期检查日志目录大小
5. 对于大规模部署，可以考虑集成 Loki + Promtail 进行集中式日志管理和分析