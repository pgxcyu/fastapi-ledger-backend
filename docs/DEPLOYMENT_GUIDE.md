# FastAPI Ledger 部署指南

## 文档概述
本文档提供了FastAPI Ledger项目的完整部署说明，包括环境准备、本地开发部署、生产环境部署以及常见问题排查。

## 项目结构
```
fastapi-ledger/
├── app/               # 应用主代码
├── alembic/           # 数据库迁移脚本
├── docs/              # 项目文档
├── nginx/             # Nginx配置
├── scripts/           # 工具脚本
├── sql/               # SQL相关文件
├── docker-compose.yml # Docker Compose配置
├── Dockerfile         # 应用Docker镜像定义
├── Makefile           # 快捷命令集合
└── requirements.txt   # Python依赖
```

## 环境准备

### 前置条件
- Docker 19.03+ 和 Docker Compose 1.25+
- Git
- 推荐：Python 3.9+（用于本地开发）

### 克隆项目
```bash
git clone [项目仓库地址]
cd fastapi-ledger
```

## 本地开发部署

### 方法1：使用Docker Compose（推荐）

#### 启动服务
```bash
# 首次运行或代码有变更时
docker compose up --build -d

# 或使用Makefile（如果已安装make工具）
make up
```

#### 查看服务状态
```bash
docker compose ps
# 或使用Makefile
make status
```

#### 查看日志
```bash
docker compose logs -f api
# 或使用Makefile
make logs
```

### 方法2：不使用Makefile的替代命令
如果系统中没有安装make工具，可以直接使用以下Docker Compose命令：

#### 启动所有服务
```bash
docker compose up --build -d
```

#### 仅更新API服务
```bash
docker compose up --build -d api
```

#### 停止服务
```bash
docker compose down
```

#### 安装make工具
```bash
choco install make
```
装好后回到项目根，再在 Git Bash/PowerShell 里跑：
```bash
make migrate
make up
make logs
```

## 任务管理

### 启动celery任务队列
```bash
celery -A app.core.celery_config worker --loglevel=info -P eventlet;
```

### 启动flower任务监控
```bash
celery -A app.core.celery_config flower;
```

### celery相关命令
```bash
# 检查正在执行的任务
celery -A app.core.celery_config inspect active

# 显示celery的一些统计信息, 比如任务执行次数
celery -A app.core.celery_config inspect stats

# 查看celery注册了哪些任务
celery -A app.core.celery_config inspect registered
```

## 数据库管理

### 数据库迁移
```bash
# 执行所有待处理的数据库迁移
docker compose exec api bash -lc "alembic upgrade head"
# 或使用Makefile
make migrate
```

### 创建新迁移
```bash
# 创建新的数据库迁移（交互式输入描述）
docker compose exec api bash -lc "alembic revision --autogenerate -m '您的迁移描述'"
# 或使用Makefile
make migrate-create
```

### 重建数据库视图
```bash
docker compose exec db psql -U postgres -d fastapi-ledger -c "CREATE OR REPLACE VIEW user_transaction_summary AS SELECT u.userid, u.username, COUNT(t.transaction_id) AS total_transactions, SUM(CASE WHEN t.type = 'INCOME' THEN t.amount ELSE 0 END) AS total_income, SUM(CASE WHEN t.type = 'EXPENSE' THEN t.amount ELSE 0 END) AS total_expense FROM users u LEFT JOIN transactions t ON t.create_userid = u.userid GROUP BY u.userid, u.username;"
# 或使用Makefile
make recreate-views
```

### 数据库备份
```bash
docker compose exec db pg_dump -U postgres -d fastapi-ledger > backup_$(date +%Y%m%d_%H%M%S).sql
# 或使用Makefile
make db-backup
```

### 连接数据库
```bash
docker compose exec db psql -U postgres -d fastapi-ledger
# 或使用Makefile
make db-shell
```

## 生产环境部署

### 环境变量配置
在生产环境中，需要配置以下关键环境变量：

```dotenv
# 数据库连接信息
DATABASE_URL=postgresql+psycopg2://user:password@db:5432/prod_db

# Redis连接信息
REDIS_URL=redis://redis:6379/0

# 安全相关配置
SECRET_KEY=your_strong_secret_key_here
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# 应用配置
ENVIRONMENT=production
DEBUG=False
```

### 使用Nginx作为反向代理
项目包含了Nginx配置，可以直接使用：

```bash
docker compose up --build -d
```

## 代码更新流程

### 1. 拉取最新代码
```bash
git pull origin main
```

### 2. 更新服务
```bash
# 仅更新API服务（不影响数据库）
docker compose up --build -d api
# 或使用Makefile
make update-api

# 或完全更新所有服务
docker compose down
docker compose up --build -d
# 或使用Makefile
make update-all
```

### 3. 执行数据库迁移（如果有模型变更）
```bash
docker compose exec api bash -lc "alembic upgrade head"
# 或使用Makefile
make migrate
```

## 常见问题排查

### 服务无法启动
- 检查Docker服务是否正常运行
- 查看日志获取详细错误信息：`docker compose logs -f`
- 确认端口未被占用

### 数据库连接失败
- 确认数据库容器已启动：`docker compose ps`
- 验证数据库凭据是否正确
- 检查数据库是否已创建

### 视图不存在错误
如果遇到`relation 'user_transaction_summary' does not exist`错误，请执行：
```bash
make recreate-views
```

## 扩展和维护

### 添加新依赖
1. 在`requirements.txt`中添加依赖
2. 重新构建API容器：`docker compose up --build -d api`

### 监控和日志
- 应用日志：`docker compose logs -f api`
- Nginx日志：`docker compose logs -f nginx`
- 数据库日志：`docker compose logs -f db`

## 安全最佳实践

1. 不要在代码仓库中存储敏感信息
2. 使用强密码和安全的密钥
3. 定期更新依赖包
4. 定期备份数据库
5. 限制API访问权限

## 开发命令速查表

| 操作 | Docker Compose命令 | Makefile命令 |
|------|-------------------|-------------|
| 启动所有服务 | `docker compose up --build -d` | `make up` |
| 仅启动API | `docker compose up --build -d api` | - |
| 停止服务 | `docker compose down` | `make down` |
| 查看日志 | `docker compose logs -f api` | `make logs` |
| 数据库迁移 | `docker compose exec api bash -lc "alembic upgrade head"` | `make migrate` |
| 创建迁移 | `docker compose exec api bash -lc "alembic revision --autogenerate -m '描述'"` | `make migrate-create` |
| 数据库备份 | `docker compose exec db pg_dump -U postgres -d fastapi-ledger > backup.sql` | `make db-backup` |

---

*最后更新：2025年11月07日*