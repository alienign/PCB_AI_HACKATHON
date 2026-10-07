from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Identity, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Analysis(Base):
    __tablename__ = "analyses"

    __table_args__ = (
        UniqueConstraint(
            "analysis_request_id",
            name="uq_analyses_analysis_request",
        ),
    )

    analysis_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
    )

    analysis_request_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "analysis_requests.analysis_request_id",
            onupdate="RESTRICT",
            ondelete="CASCADE",
            name="fk_analyses_analysis_request",
        ),
        nullable=False,
    )

    model_version_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "model_versions.model_version_id",
            onupdate="RESTRICT",
            ondelete="RESTRICT",
            name="fk_analyses_model_version",
        ),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )