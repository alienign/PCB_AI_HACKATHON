from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Identity, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ModelVersion(Base):
    __tablename__ = "model_versions"

    __table_args__ = (
        UniqueConstraint(
            "model_name",
            "version_name",
            name="uq_model_versions_name_version",
        ),
        CheckConstraint(
            "btrim(model_name) <> ''",
            name="ck_model_versions_model_name_not_blank",
        ),
        CheckConstraint(
            "btrim(version_name) <> ''",
            name="ck_model_versions_version_name_not_blank",
        ),
        CheckConstraint(
            "weights_hash IS NULL OR btrim(weights_hash) <> ''",
            name="ck_model_versions_weights_hash_not_blank",
        ),
    )

    model_version_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
    )

    model_name: Mapped[str] = mapped_column(Text, nullable=False)
    version_name: Mapped[str] = mapped_column(Text, nullable=False)
    weights_hash: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )