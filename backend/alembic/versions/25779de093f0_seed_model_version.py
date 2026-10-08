"""seed model version

Revision ID: 25779de093f0
Revises: 3a8b504dfd1e
Create Date: 2026-10-08 16:42:43.384723

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '25779de093f0'
down_revision: Union[str, Sequence[str], None] = '3a8b504dfd1e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Register the test YOLOv8 model."""
    model_versions = sa.table(
        "model_versions",
        sa.column("model_name", sa.Text()),
        sa.column("version_name", sa.Text()),
        sa.column("weights_hash", sa.Text()),
    )

    op.bulk_insert(
        model_versions,
        [
            {
                "model_name": "pcb-defect-yolov8m-dspcbsd",
                "version_name": "best.pt",
                "weights_hash": (
                    "e0978435538c462009835c810787e320"
                    "30154c40918b7211a0b3f409ec36453c"
                ),
            }
        ],
    )

def downgrade() -> None:
    """Remove the registered test model version."""
    op.execute(
        sa.text(
            """
            DELETE FROM model_versions
            WHERE model_name = 'pcb-defect-yolov8m-dspcbsd'
              AND version_name = 'best.pt'
              AND weights_hash = (
                  'e0978435538c462009835c810787e320'
                  || '30154c40918b7211a0b3f409ec36453c'
              )
            """
        )
    )
