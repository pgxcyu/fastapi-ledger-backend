"""增加枚举定义

Revision ID: 129f5d812af0
Revises: f9bdfc011b5d
Create Date: 2025-11-13 16:06:20.528511

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '129f5d812af0'
down_revision: Union[str, Sequence[str], None] = 'f9bdfc011b5d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 检查列是否存在
    conn = op.get_bind()
    column_exists = conn.execute(
        sa.text("SELECT column_name FROM information_schema.columns WHERE table_name='resources' AND column_name='menu_type'")
    ).scalar() is not None
    
    # 删除旧的枚举类型（如果存在）
    op.execute("DROP TYPE IF EXISTS menutype CASCADE;")
    
    # 创建新的枚举类型
    op.execute("""
    CREATE TYPE menutype AS ENUM ('GRID', 'LIST', 'CHART', 'DIR');
    """)
    
    if column_exists:
        # 如果列存在，修改它
        op.alter_column('resources', 'menu_type',
                       existing_type=postgresql.ENUM('GRID', 'LIST', 'CHART', 'DIR', name='menutype'),
                       nullable=True)
    else:
        # 如果列不存在，添加它
        op.add_column('resources', sa.Column('menu_type', postgresql.ENUM('GRID', 'LIST', 'CHART', 'DIR', name='menutype'), nullable=True))

def downgrade() -> None:
    # 在降级前，将所有空值设置为默认值
    conn = op.get_bind()
    conn.execute(sa.text("UPDATE resources SET menu_type = 'GRID' WHERE menu_type IS NULL"))
    
    # 修改menu_type列为非空
    op.alter_column('resources', 'menu_type',
                   existing_type=postgresql.ENUM('GRID', 'LIST', 'CHART', 'DIR', name='menutype'),
                   nullable=True)
    
    # 降级不需要删除枚举类型，因为upgrade已经处理了枚举的重建
