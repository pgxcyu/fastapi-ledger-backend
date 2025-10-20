"""missing version

Revision ID: b1b9047fb3e3
Revises: 
Create Date: 2025-10-17 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1b9047fb3e3'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 空的升级脚本，仅作为版本占位符
    pass


def downgrade() -> None:
    """Downgrade schema."""
    # 空的降级脚本
    pass