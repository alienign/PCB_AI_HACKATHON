from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.analysis import Analysis
from app.models.analysis_request import AnalysisRequest
from app.models.detection import Detection
from app.repositories.analysis_repository import create_analysis
from app.repositories.detection_repository import (
    create_detection,
    get_defect_type_by_code,
)
from app.services.ml_service import MLDetection


def save_analysis_result(
    db: Session,
    *,
    request_id: int,
    model_version_id: int,
    detections: list[MLDetection],
) -> Analysis:
    """
    Атомарно сохраняет Analysis, Detection
    и переводит AnalysisRequest в completed.
    """

    try:
        request = db.get(
            AnalysisRequest,
            request_id,
            with_for_update=True,
        )

        if request is None:
            raise ValueError(
                f"AnalysisRequest {request_id} not found."
            )

        if request.request_status != "processing":
            raise ValueError(
                "AnalysisRequest must be processing."
            )

        analysis = create_analysis(
            db,
            analysis_request_id=request_id,
            model_version_id=model_version_id,
        )

        for item in detections:
            defect_type = get_defect_type_by_code(
                db,
                item.defect_code,
            )

            if defect_type is None:
                raise ValueError(
                    f"Unknown defect type: {item.defect_code}"
                )

            create_detection(
                db,
                analysis_id=analysis.analysis_id,
                defect_type_id=defect_type.defect_type_id,
                confidence=item.confidence,
                bbox_x=item.x_min,
                bbox_y=item.y_min,
                bbox_width=item.x_max - item.x_min,
                bbox_height=item.y_max - item.y_min,
            )

        request.request_status = "completed"
        request.finished_at = func.now()
        request.error_code = None
        request.error_message = None

        db.flush()
        db.commit()
        db.refresh(analysis)

        return analysis

    except Exception:
        db.rollback()
        raise