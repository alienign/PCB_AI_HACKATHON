from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Float,
    ForeignKey,
    Identity,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Detection(Base):
    __tablename__ = "detections"

    __table_args__ = (
        CheckConstraint(
            "confidence >= 0.0 AND confidence <= 1.0",
            name="ck_detections_confidence",
        ),
        CheckConstraint(
            "bbox_x >= 0.0 AND bbox_x <= 1.0",
            name="ck_detections_bbox_x",
        ),
        CheckConstraint(
            "bbox_y >= 0.0 AND bbox_y <= 1.0",
            name="ck_detections_bbox_y",
        ),
        CheckConstraint(
            "bbox_width > 0.0 AND bbox_width <= 1.0",
            name="ck_detections_bbox_width",
        ),
        CheckConstraint(
            "bbox_height > 0.0 AND bbox_height <= 1.0",
            name="ck_detections_bbox_height",
        ),
        CheckConstraint(
            "bbox_x + bbox_width <= 1.0",
            name="ck_detections_bbox_horizontal_bounds",
        ),
        CheckConstraint(
            "bbox_y + bbox_height <= 1.0",
            name="ck_detections_bbox_vertical_bounds",
        ),
        Index(
            "ix_detections_analysis",
            "analysis_id",
        ),
        Index(
            "ix_detections_defect_type",
            "defect_type_id",
        ),
    )

    detection_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
    )

    analysis_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "analyses.analysis_id",
            onupdate="RESTRICT",
            ondelete="CASCADE",
            name="fk_detections_analysis",
        ),
        nullable=False,
    )

    defect_type_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "defect_types.defect_type_id",
            onupdate="RESTRICT",
            ondelete="RESTRICT",
            name="fk_detections_defect_type",
        ),
        nullable=False,
    )

    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    bbox_x: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_y: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_width: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_height: Mapped[float] = mapped_column(Float, nullable=False)
