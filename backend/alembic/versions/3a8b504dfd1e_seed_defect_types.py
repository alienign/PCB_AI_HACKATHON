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
    """Seed defect types used by the ML model."""
    defect_types = sa.table(
        "defect_types",
        sa.column("defect_code", sa.Text()),
        sa.column("defect_name", sa.Text()),
    )

    op.bulk_insert(
        defect_types,
        [
            {"defect_code": "short", "defect_name": "Short"},
            {"defect_code": "spur", "defect_name": "Spur"},
            {
                "defect_code": "spurious_copper",
                "defect_name": "Spurious Copper",
            },
            {"defect_code": "open", "defect_name": "Open"},
            {"defect_code": "mouse_bite", "defect_name": "Mouse Bite"},
            {
                "defect_code": "hole_breakout",
                "defect_name": "Hole Breakout",
            },
            {
                "defect_code": "conductor_scratch",
                "defect_name": "Conductor Scratch",
            },
            {
                "defect_code": "conductor_foreign_object",
                "defect_name": "Conductor Foreign Object",
            },
            {
                "defect_code": "base_material_foreign_object",
                "defect_name": "Base Material Foreign Object",
            },
        ],
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
