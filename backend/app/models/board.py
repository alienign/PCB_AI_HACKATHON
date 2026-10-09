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


class Board(Base):
    __tablename__ = "boards"

    __table_args__ = (
        CheckConstraint(
            "btrim(board_label) <> ''",
            name="ck_boards_label_not_blank",
        ),
        CheckConstraint(
            "serial_number IS NULL OR btrim(serial_number) <> ''",
            name="ck_boards_serial_number_not_blank",
        ),
        Index(
            "ix_boards_created_by_account_created_at",
            "created_by_account_id",
            column("created_at").desc(),
        ),
    )

    board_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
    )

    created_by_account_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "accounts.account_id",
            onupdate="RESTRICT",
            ondelete="RESTRICT",
            name="fk_boards_created_by_account",
        ),
        nullable=False,
    )

    board_label: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    serial_number: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    board_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
