"""seed defect types

Revision ID: 3a8b504dfd1e
Revises: 44eaf0d54bfd
Create Date: 2026-10-08 13:27:45.987214

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3a8b504dfd1e'
down_revision: Union[str, Sequence[str], None] = '44eaf0d54bfd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Seed defect types without creating duplicates."""
    op.execute(
        """
        INSERT INTO defect_types (defect_code, defect_name)
        VALUES
            ('short', 'Short'),
            ('spur', 'Spur'),
            ('spurious_copper', 'Spurious Copper'),
            ('open', 'Open'),
            ('mouse_bite', 'Mouse Bite'),
            ('hole_breakout', 'Hole Breakout'),
            ('conductor_scratch', 'Conductor Scratch'),
            ('conductor_foreign_object', 'Conductor Foreign Object'),
            ('base_material_foreign_object', 'Base Material Foreign Object')
        ON CONFLICT (defect_code) DO NOTHING
        """
    )


def downgrade() -> None:
    """Remove seeded defect types."""
    op.execute(
        sa.text(
            """
            DELETE FROM defect_types
            WHERE defect_code IN (
                'short',
                'spur',
                'spurious_copper',
                'open',
                'mouse_bite',
                'hole_breakout',
                'conductor_scratch',
                'conductor_foreign_object',
                'base_material_foreign_object'
            )
            """
        )
    )
