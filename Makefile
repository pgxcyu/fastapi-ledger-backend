# 安全的Docker Compose命令集

# 启动所有服务（包含构建）
up:
	docker compose up --build -d

# 启动所有服务（不构建）
start:
	docker compose up -d

# 安全停止服务（不删除数据卷）
down:
	docker compose down

# ⚠️ 危险：删除所有数据卷 ⚠️
down-clean:
	echo "警告：此命令将删除所有数据库数据卷！"
	echo "按 Ctrl+C 取消，或按 Enter 继续..."
	@read _
	docker compose down -v

# 查看API服务日志
logs:
	docker compose logs -f api

# 进入API容器shell
shell:
	docker compose exec api bash

# 数据库操作
db-shell:
	docker compose exec db psql -U postgres -d fastapi-ledger

# 备份数据库
db-backup:
	docker compose exec db pg_dump -U postgres -d fastapi-ledger > backup_$(shell date +%Y%m%d_%H%M%S).sql
	echo "数据库备份完成：backup_$(shell date +%Y%m%d_%H%M%S).sql"

# Alembic数据库迁移
migrate:
	docker compose exec api bash -lc "alembic upgrade head"

# 创建新的Alembic迁移脚本（带自动生成）
migrate-create:
	echo "请输入迁移描述:"
	@read desc && docker compose exec api bash -lc "alembic revision --autogenerate -m \"$$desc\""

# 查看迁移历史
migrate-history:
	docker compose exec api bash -lc "alembic history"

# 代码更新命令
# 1. 安全更新API服务（不影响数据库）
update-api:
	docker compose up --build -d api
	echo "API服务已更新"

# 2. 完全更新所有服务（不删除数据）
update-all:
	docker compose down
	docker compose up --build -d
	echo "所有服务已更新"

# 重建数据库视图
recreate-views:
	docker compose exec db psql -U postgres -d fastapi-ledger -c "CREATE OR REPLACE VIEW user_transaction_summary AS SELECT u.userid, u.username, COUNT(t.transaction_id) AS total_transactions, SUM(CASE WHEN t.type = 'INCOME' THEN t.amount ELSE 0 END) AS total_income, SUM(CASE WHEN t.type = 'EXPENSE' THEN t.amount ELSE 0 END) AS total_expense FROM users u LEFT JOIN transactions t ON t.create_userid = u.userid GROUP BY u.userid, u.username;"
	echo "数据库视图已重建"

# 列出服务状态
status:
	docker compose ps

# 清理未使用的Docker资源
clean:
	docker system prune -f
	docker volume prune -f
