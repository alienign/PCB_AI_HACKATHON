from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.defect_type import DefectType
from app.models.detection import Detection


def get_defect_type_by_code(
    db: Session,
    defect_code: str,
) -> DefectType | None:
    statement = select(DefectType).where(
        DefectType.defect_code == defect_code
    )

    return db.scalar(statement)


def create_detection(
    db: Session,
    *,
    analysis_id: int,
    defect_type_id: int,
    confidence: float,
    bbox_x: float,
    bbox_y: float,
    bbox_width: float,
    bbox_height: float,
) -> Detection:
    detection = Detection(
        analysis_id=analysis_id,
        defect_type_id=defect_type_id,
        confidence=confidence,
        bbox_x=bbox_x,
        bbox_y=bbox_y,
        bbox_width=bbox_width,
        bbox_height=bbox_height,
    )

    db.add(detection)
    db.flush()

    return detection