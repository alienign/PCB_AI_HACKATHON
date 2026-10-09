"""initial seed data

Revision ID: 0002_initial_seed_data
Revises: 0001_initial_schema
"""

from typing import Sequence, Union

from alembic import op


revision: str = "0002_initial_seed_data"
down_revision: Union[str, Sequence[str], None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


DEFECT_CODES = (
    "short",
    "spur",
    "spurious_copper",
    "open",
    "mouse_bite",
    "hole_breakout",
    "conductor_scratch",
    "conductor_foreign_object",
    "base_material_foreign_object",
)


def upgrade() -> None:
    # Системный demo account для single-user MVP.
    op.execute(
        """
        INSERT INTO accounts (login, display_name)
        VALUES ('demo', 'demo')
        ON CONFLICT (login) DO NOTHING
        """
    )

    # Девять классов дефектов, зафиксированных для ML-модели.
    for defect_code in DEFECT_CODES:
        op.execute(
            f"""
            INSERT INTO defect_types (defect_code, defect_name)
            VALUES ('{defect_code}', '{defect_code}')
            ON CONFLICT (defect_code) DO NOTHING
            """
        )


def downgrade() -> None:
    # Удаляем seed-данные только если они ещё не используются.
    # Это защищает существующие пользовательские данные от повреждения.

    op.execute(
        """
        DELETE FROM defect_types AS dt
        WHERE dt.defect_code IN (
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
        AND NOT EXISTS (
            SELECT 1
            FROM detections AS d
            WHERE d.defect_type_id = dt.defect_type_id
        )
        """
    )

    op.execute(
        """
        DELETE FROM accounts AS a
        WHERE a.login = 'demo'
        AND NOT EXISTS (
            SELECT 1
            FROM boards AS b
            WHERE b.created_by_account_id = a.account_id
        )
        AND NOT EXISTS (
            SELECT 1
            FROM images AS i
            WHERE i.uploaded_by_account_id = a.account_id
        )
        AND NOT EXISTS (
            SELECT 1
            FROM analysis_requests AS ar
            WHERE ar.account_id = a.account_id
        )
        """
    )