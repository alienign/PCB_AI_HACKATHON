"""merge backend migration branches

Revision ID: 92f662858fce
Revises: 25779de093f0, 0002_initial_seed_data
Create Date: 2026-10-08 18:42:28.298797

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '92f662858fce'
down_revision: Union[str, Sequence[str], None] = ('25779de093f0', '0002_initial_seed_data')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
