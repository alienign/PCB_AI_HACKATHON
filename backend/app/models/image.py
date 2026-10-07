from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Image(Base):
    __tablename__ = "images"

    __table_args__ = (
        UniqueConstraint(
            "storage_key",
            name="uq_images_storage_key",
        ),
        CheckConstraint(
            "btrim(storage_key) <> ''",
            name="ck_images_storage_key_not_blank",
        ),
        CheckConstraint(
            "btrim(original_filename) <> ''",
            name="ck_images_original_filename_not_blank",
        ),
        CheckConstraint(
            "btrim(mime_type) <> ''",
            name="ck_images_mime_type_not_blank",
        ),
        CheckConstraint(
            "file_size IS NULL OR file_size > 0",
            name="ck_images_file_size_positive",
        ),
        CheckConstraint(
            "file_hash IS NULL OR btrim(file_hash) <> ''",
            name="ck_images_file_hash_not_blank",
        ),
    )

    image_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
    )

    board_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "boards.board_id",
            onupdate="RESTRICT",
            ondelete="RESTRICT",
            name="fk_images_board",
        ),
        nullable=False,
    )

    uploaded_by_account_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "accounts.account_id",
            onupdate="RESTRICT",
            ondelete="RESTRICT",
            name="fk_images_uploaded_by_account",
        ),
        nullable=False,
    )

    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    original_filename: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str] = mapped_column(Text, nullable=False)

    file_size: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    file_hash: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )