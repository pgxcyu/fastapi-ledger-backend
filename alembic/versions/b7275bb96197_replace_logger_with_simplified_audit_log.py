"""replace_logger_with_simplified_audit_log

Revision ID: b7275bb96197
Revises: 3627d9edccfe
Create Date: 2025-11-19 12:02:50.567428

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b7275bb96197'
down_revision: Union[str, Sequence[str], None] = '3627d9edccfe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 删除旧的loggers表和相关索引
    op.drop_index('idx_audit_action_result', table_name='loggers')
    op.drop_index('idx_audit_request_id', table_name='loggers')
    op.drop_index('idx_audit_resource', table_name='loggers')
    op.drop_index('idx_audit_risk_level', table_name='loggers')
    op.drop_index('idx_audit_session', table_name='loggers')
    op.drop_index('idx_audit_userid_created', table_name='loggers')
    op.drop_index('ix_loggers_id', table_name='loggers')
    op.drop_index('ix_loggers_userid', table_name='loggers')
    op.drop_table('loggers')
    
    # 创建新的简化审计日志表
    op.create_table('audit_logs',
    sa.Column('audit_id', sa.String(length=32), nullable=False, comment='审计唯一标识'),
    sa.Column('user_id', sa.String(length=32), nullable=False, comment='操作用户ID'),
    sa.Column('user_name', sa.String(length=100), nullable=True, comment='操作用户名'),
    sa.Column('session_id', sa.String(length=32), nullable=True, comment='会话ID'),
    sa.Column('ip_address', sa.String(length=45), nullable=False, comment='客户端IP地址'),
    sa.Column('user_agent', sa.String(length=500), nullable=True, comment='用户代理'),
    sa.Column('request_method', sa.String(length=10), nullable=False, comment='HTTP请求方法'),
    sa.Column('request_path', sa.String(length=255), nullable=False, comment='请求路径'),
    sa.Column('operation_type', sa.String(length=20), nullable=False, comment='操作类型(CREATE/UPDATE/DELETE/READ/LOGIN/LOGOUT)'),
    sa.Column('operation_module', sa.String(length=50), nullable=False, comment='操作模块'),
    sa.Column('operation_description', sa.String(length=200), nullable=False, comment='操作描述'),
    sa.Column('resource_type', sa.String(length=50), nullable=False, comment='资源类型(USER/TRANSACTION/ROLE/SYSTEM)'),
    sa.Column('resource_id', sa.String(length=32), nullable=True, comment='资源ID'),
    sa.Column('resource_name', sa.String(length=200), nullable=True, comment='资源名称'),
    sa.Column('audit_level', sa.String(length=20), nullable=False, comment='审计级别(INFO/WARNING/ERROR/CRITICAL)'),
    sa.Column('risk_level', sa.String(length=20), nullable=False, comment='风险级别(LOW/MEDIUM/HIGH/CRITICAL)'),
    sa.Column('sensitive_flag', sa.Boolean(), nullable=False, comment='敏感操作标记'),
    sa.Column('operation_result', sa.String(length=20), nullable=False, comment='操作结果(SUCCESS/FAILURE)'),
    sa.Column('error_message', sa.Text(), nullable=True, comment='错误信息'),
    sa.Column('before_data', sa.Text(), nullable=True, comment='操作前数据(JSON)'),
    sa.Column('after_data', sa.Text(), nullable=True, comment='操作后数据(JSON)'),
    sa.Column('business_context', sa.Text(), nullable=True, comment='业务上下文'),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('audit_id')
    )
    
    # 添加核心审计索引
    op.create_index('idx_audit_user_created', 'audit_logs', ['user_id', 'created_at'])
    op.create_index('idx_audit_operation', 'audit_logs', ['operation_type', 'operation_result'])
    op.create_index('idx_audit_resource', 'audit_logs', ['resource_type', 'resource_id'])
    op.create_index('idx_audit_level', 'audit_logs', ['audit_level', 'created_at'])


def downgrade() -> None:
    """Downgrade schema."""
    # 删除审计索引
    op.drop_index('idx_audit_level', 'audit_logs')
    op.drop_index('idx_audit_resource', 'audit_logs')
    op.drop_index('idx_audit_operation', 'audit_logs')
    op.drop_index('idx_audit_user_created', 'audit_logs')
    
    # 删除审计表
    op.drop_table('audit_logs')
    
    # 重建旧的loggers表
    op.create_table('loggers',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('userid', sa.VARCHAR(length=32), autoincrement=False, nullable=False),
    sa.Column('action', sa.VARCHAR(length=255), autoincrement=False, nullable=False),
    sa.Column('info', sa.VARCHAR(length=1000), autoincrement=False, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True),
    sa.Column('ip_address', sa.VARCHAR(length=45), autoincrement=False, nullable=True, comment='IP地址'),
    sa.Column('user_agent', sa.VARCHAR(length=500), autoincrement=False, nullable=True, comment='用户代理'),
    sa.Column('request_method', sa.VARCHAR(length=10), autoincrement=False, nullable=True, comment='HTTP方法'),
    sa.Column('request_path', sa.VARCHAR(length=255), autoincrement=False, nullable=True, comment='请求路径'),
    sa.Column('request_id', sa.VARCHAR(length=32), autoincrement=False, nullable=True, comment='请求ID'),
    sa.Column('session_id', sa.VARCHAR(length=32), autoincrement=False, nullable=True, comment='会话ID'),
    sa.Column('audit_level', sa.VARCHAR(length=20), autoincrement=False, nullable=True, comment='审计级别'),
    sa.Column('operation_type', sa.VARCHAR(length=50), autoincrement=False, nullable=True, comment='操作类型'),
    sa.Column('resource_type', sa.VARCHAR(length=50), autoincrement=False, nullable=True, comment='资源类型'),
    sa.Column('resource_id', sa.VARCHAR(length=32), autoincrement=False, nullable=True, comment='资源ID'),
    sa.Column('operation_result', sa.VARCHAR(length=20), autoincrement=False, nullable=True, comment='操作结果'),
    sa.Column('risk_level', sa.VARCHAR(length=20), autoincrement=False, nullable=True, comment='风险级别'),
    sa.Column('before_data', sa.TEXT(), autoincrement=False, nullable=True, comment='操作前数据'),
    sa.Column('after_data', sa.TEXT(), autoincrement=False, nullable=True, comment='操作后数据'),
    sa.Column('sensitive_flag', sa.BOOLEAN(), autoincrement=False, nullable=True, comment='敏感操作标记'),
    sa.Column('compliance_flag', sa.BOOLEAN(), autoincrement=False, nullable=True, comment='合规标记'),
    sa.Column('business_context', sa.TEXT(), autoincrement=False, nullable=True, comment='业务上下文'),
    sa.ForeignKeyConstraint(['userid'], ['users.userid'], name='loggers_userid_fkey'),
    sa.PrimaryKeyConstraint('id', name='loggers_pkey')
    )
    op.create_index('ix_loggers_userid', 'loggers', ['userid'], unique=False)
    op.create_index('ix_loggers_id', 'loggers', ['id'], unique=False)
    op.create_index('idx_audit_userid_created', 'loggers', ['userid', 'created_at'], unique=False)
    op.create_index('idx_audit_session', 'loggers', ['session_id', 'created_at'], unique=False)
    op.create_index('idx_audit_risk_level', 'loggers', ['risk_level', 'created_at'], unique=False)
    op.create_index('idx_audit_resource', 'loggers', ['resource_type', 'resource_id'], unique=False)
    op.create_index('idx_audit_request_id', 'loggers', ['request_id'], unique=False)
    op.create_index('idx_audit_action_result', 'loggers', ['action', 'operation_result'], unique=False)