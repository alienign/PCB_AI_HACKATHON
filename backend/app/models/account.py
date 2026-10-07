from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Identity,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Account(Base):
    __tablename__ = "accounts"

    __table_args__ = (
        CheckConstraint(
            "btrim(login) <> ''",
            name="ck_accounts_login_not_blank",
        ),
        CheckConstraint(
            "btrim(display_name) <> ''",
            name="ck_accounts_display_name_not_blank",
        ),
        CheckConstraint(
            "email IS NULL OR btrim(email) <> ''",
            name="ck_accounts_email_not_blank",
        ),
    )

    account_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
    )

    login: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        unique=True,
    )

    display_name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    email: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
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