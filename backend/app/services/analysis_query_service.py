from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.analysis import Analysis
from app.models.analysis_request import AnalysisRequest
from app.models.defect_type import DefectType
from app.models.detection import Detection
from app.models.model_version import ModelVersion


def get_analysis_result(
    db: Session,
    request_id: int,
) -> dict | None:
    """
    Возвращает результат анализа по AnalysisRequest ID.

    Для created/processing/failed возвращает статус
    без результатов обнаружения.

    Для completed возвращает модель и список дефектов.

    Если запрос не существует, возвращает None.
    """

    request = db.get(AnalysisRequest, request_id)

    if request is None:
        return None

    result = {
        "request_id": request.analysis_request_id,
        "image_id": request.image_id,
        "status": request.request_status,
        "error_code": request.error_code,
        "error_message": request.error_message,
        "analysis_id": None,
        "model": None,
        "detections_count": 0,
        "detections": [],
    }

    if request.request_status != "completed":
        return result

    statement = (
        select(Analysis, ModelVersion)
        .join(
            ModelVersion,
            Analysis.model_version_id == ModelVersion.model_version_id,
        )
        .where(
            Analysis.analysis_request_id == request_id,
        )
    )

    row = db.execute(statement).one_or_none()

    if row is None:
        raise RuntimeError(
            f"Completed request {request_id} has no Analysis."
        )

    analysis, model = row

    result["analysis_id"] = analysis.analysis_id

    result["model"] = {
        "model_version_id": model.model_version_id,
        "name": model.model_name,
        "version": model.version_name,
    }

    detections_statement = (
        select(Detection, DefectType)
        .join(
            DefectType,
            Detection.defect_type_id == DefectType.defect_type_id,
        )
        .where(
            Detection.analysis_id == analysis.analysis_id,
        )
        .order_by(Detection.detection_id)
    )

    detections = []

    for detection, defect_type in db.execute(
        detections_statement
    ):
        detections.append(
            {
                "detection_id": detection.detection_id,
                "defect_type_id": defect_type.defect_type_id,
                "defect_code": defect_type.defect_code,
                "defect_name": defect_type.defect_name,
                "confidence": detection.confidence,
                "bbox": {
                    "x": detection.bbox_x,
                    "y": detection.bbox_y,
                    "width": detection.bbox_width,
                    "height": detection.bbox_height,
                },
            }
        )

    result["detections"] = detections
    result["detections_count"] = len(detections)

    return result
