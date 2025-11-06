# alembic/env.py
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# 关键1：引入你的设置和 Base
from app.core.config import settings
from app.db.models import Base  # 确保这里导入的是所有模型的 Base

# 关键2：**强制导入所有模型模块**，否则 autogenerate 检测不到
# 例如：
from app.db.models import User, Transaction, Fileassets, Logger

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 关键3：把 URL 写回 Alembic config（避免用死在 alembic.ini 的占位串）
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,      # 字段类型变更也能检测
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()