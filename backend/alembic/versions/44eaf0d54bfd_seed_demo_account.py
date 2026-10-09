"""seed demo account

Revision ID: 44eaf0d54bfd
Revises: 0001_initial_schema
Create Date: 2026-10-08 11:17:19.053410
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "44eaf0d54bfd"
down_revision: Union[str, Sequence[str], None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the demo account if it does not already exist."""
    op.execute(
        """
        INSERT INTO accounts (login, display_name)
        VALUES ('demo', 'Demo User')
        ON CONFLICT (login) DO NOTHING
        """
    )


def downgrade() -> None:
    """Remove the demo account."""
    op.execute(
        sa.text("DELETE FROM accounts WHERE login = :login").bindparams(
            login="demo"
        )
    )
