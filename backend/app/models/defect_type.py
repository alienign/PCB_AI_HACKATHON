from sqlalchemy import BigInteger, Boolean, CheckConstraint, Identity, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DefectType(Base):
    __tablename__ = "defect_types"

    __table_args__ = (
        CheckConstraint(
            "btrim(defect_code) <> ''",
            name="ck_defect_types_code_not_blank",
        ),
        CheckConstraint(
            "btrim(defect_name) <> ''",
            name="ck_defect_types_name_not_blank",
        ),
        CheckConstraint(
            "defect_code ~ '^[a-z0-9][a-z0-9_]*$'",
            name="ck_defect_types_code_format",
        ),
    )

    defect_type_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
    )

    defect_code: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        unique=True,
    )

    defect_name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
    )