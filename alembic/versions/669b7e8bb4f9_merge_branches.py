"""Merge branches

Revision ID: 669b7e8bb4f9
Revises: b1b9047fb3e3, cc41ba1ff913
Create Date: 2025-10-20 08:40:53.836972

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '669b7e8bb4f9'
down_revision: Union[str, Sequence[str], None] = ('b1b9047fb3e3', 'cc41ba1ff913')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
