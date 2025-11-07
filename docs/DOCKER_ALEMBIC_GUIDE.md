# 在Docker中运行Alembic命令指南

本文档介绍如何在Docker环境中运行Alembic数据库迁移命令。

## 前提条件

确保以下服务已经启动并运行：

1. Docker和Docker Compose已安装
2. 项目的Docker容器已启动（使用`docker-compose up -d`）

## 方法一：在运行中的API容器中执行Alembic命令

这是最常用的方法，直接在运行中的API容器内执行Alembic命令。

### 1. 查看正在运行的容器

首先，确认API容器正在运行：

```bash
docker-compose ps
```

### 2. 执行Alembic命令

使用`docker-compose exec`命令在API容器中执行Alembic命令：

#### 升级数据库到最新版本

```bash
docker-compose exec api alembic upgrade head
```

#### 创建新的迁移脚本（自动生成）

```bash
docker-compose exec api alembic revision --autogenerate -m "描述你的迁移变更"
```

#### 查看迁移历史

```bash
docker-compose exec api alembic history
```

#### 升级到特定版本

```bash
docker-compose exec api alembic upgrade <revision_id>
```

#### 降级到特定版本

```bash
docker-compose exec api alembic downgrade <revision_id>
```

## 方法二：使用临时容器运行Alembic命令

如果API容器未运行或你不想在其中执行命令，可以创建一个临时容器：

```bash
docker-compose run --rm api alembic upgrade head
```

## 方法三：使用docker exec命令（替代方法）

如果你知道容器的具体名称，可以使用`docker exec`命令：

```bash
docker exec -it fastapi-ledger-api-1 alembic upgrade head
```

## 注意事项

1. **环境变量**：Alembic配置使用了环境变量（PG_USER, PG_PASSWORD, PG_DB），这些变量会从`.env`文件中自动加载到容器中。

2. **数据库连接**：确保数据库服务（`db`）正在运行，因为Alembic需要连接到数据库才能执行迁移。

3. **修改Alembic配置**：如果需要修改Alembic配置，请编辑`alembic.ini`文件。数据库连接URL已配置为使用容器间通信：`postgresql+psycopg://${PG_USER}:${PG_PASSWORD}@db:5432/${PG_DB}`

4. **迁移脚本**：新的迁移脚本会在`alembic/versions/`目录中生成。

## 常见问题排查

### 数据库连接失败

- 确保数据库服务正在运行：`docker-compose ps db`
- 检查环境变量是否正确设置：`docker-compose exec api env | grep PG_`

### Alembic命令未找到

- 确保`requirements.txt`中包含了Alembic依赖
- 重建API容器：`docker-compose build api`

### 迁移冲突

- 查看详细的迁移历史：`docker-compose exec api alembic history --verbose`
- 考虑使用`stamp`命令来标记当前数据库版本：`docker-compose exec api alembic stamp <revision_id>`

## 示例工作流

1. 对模型进行更改
2. 创建自动迁移：`docker-compose exec api alembic revision --autogenerate -m "添加新字段"
3. 审查生成的迁移脚本（位于`alembic/versions/`目录）
4. 应用迁移：`docker-compose exec api alembic upgrade head`
5. 验证更改已应用

## 备份和恢复

在执行重要迁移之前，建议备份数据库：

```bash
docker-compose exec db pg_dump -U ${PG_USER} -d ${PG_DB} > backup_$(date +%Y%m%d_%H%M%S).sql
```

要恢复备份：

```bash
cat backup.sql | docker-compose exec -T db psql -U ${PG_USER} -d ${PG_DB}
```