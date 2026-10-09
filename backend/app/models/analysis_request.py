from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Text,
    column,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AnalysisRequest(Base):
    __tablename__ = "analysis_requests"

    __table_args__ = (
        CheckConstraint(
            "request_status IN ('created', 'processing', 'completed', 'failed')",
            name="ck_analysis_requests_status",
        ),
        CheckConstraint(
            "started_at IS NULL OR started_at >= created_at",
            name="ck_analysis_requests_started_after_created",
        ),
        CheckConstraint(
            "finished_at IS NULL OR finished_at >= created_at",
            name="ck_analysis_requests_finished_after_created",
        ),
        CheckConstraint(
            "finished_at IS NULL OR started_at IS NULL OR finished_at >= started_at",
            name="ck_analysis_requests_finished_after_started",
        ),
        CheckConstraint(
            "error_code IS NULL OR btrim(error_code) <> ''",
            name="ck_analysis_requests_error_code_not_blank",
        ),
        CheckConstraint(
            "error_message IS NULL OR btrim(error_message) <> ''",
            name="ck_analysis_requests_error_message_not_blank",
        ),
        CheckConstraint(
            """
            (
                request_status = 'created'
                AND started_at IS NULL
                AND finished_at IS NULL
                AND error_code IS NULL
                AND error_message IS NULL
            )
            OR
            (
                request_status = 'processing'
                AND started_at IS NOT NULL
                AND finished_at IS NULL
                AND error_code IS NULL
                AND error_message IS NULL
            )
            OR
            (
                request_status = 'completed'
                AND started_at IS NOT NULL
                AND finished_at IS NOT NULL
                AND error_code IS NULL
                AND error_message IS NULL
            )
            OR
            (
                request_status = 'failed'
                AND finished_at IS NOT NULL
                AND error_code IS NOT NULL
            )
            """,
            name="ck_analysis_requests_state_consistency",
        ),
        Index(
            "ix_analysis_requests_account_created_at",
            "account_id",
            column("created_at").desc(),
        ),
        Index(
            "ix_analysis_requests_image_created_at",
            "image_id",
            column("created_at").desc(),
        ),
        Index(
            "ix_analysis_requests_status_created_at",
            "request_status",
            column("created_at").desc(),
        ),
    )

    analysis_request_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
    )

    account_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "accounts.account_id",
            onupdate="RESTRICT",
            ondelete="RESTRICT",
            name="fk_analysis_requests_account",
        ),
        nullable=False,
    )

    image_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "images.image_id",
            onupdate="RESTRICT",
            ondelete="RESTRICT",
            name="fk_analysis_requests_image",
        ),
        nullable=False,
    )

    request_status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default="created",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    error_code: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
