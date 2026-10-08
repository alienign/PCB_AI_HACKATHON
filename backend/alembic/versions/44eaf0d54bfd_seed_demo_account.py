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
    """Create the demo account required by the hackathon MVP."""
    accounts = sa.table(
        "accounts",
        sa.column("login", sa.Text()),
        sa.column("display_name", sa.Text()),
    )

    op.bulk_insert(
        accounts,
        [
            {
                "login": "demo",
                "display_name": "Demo User",
            }
        ],
    )


def downgrade() -> None:
    """Remove the demo account."""
    op.execute(
        sa.text("DELETE FROM accounts WHERE login = :login").bindparams(
            login="demo"
        )
    )
