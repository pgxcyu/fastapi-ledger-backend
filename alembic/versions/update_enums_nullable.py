"""更新枚举定义，支持可空

Revision ID: update_enums_nullable
Revises: 129f5d812af0
Create Date: 2023-07-14 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'update_enums_nullable'
down_revision = '129f5d812af0'
branch_labels = None
depends_on = None

def upgrade() -> None:
    pass

def downgrade() -> None:
    pass