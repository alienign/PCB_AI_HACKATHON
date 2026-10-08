from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.analysis import Analysis
from app.models.analysis_request import AnalysisRequest
from app.models.detection import Detection


def get_analysis_history(
    db: Session,
    account_id: int,
    limit: int = 20,
    offset: int = 0,
) -> list[dict]:
    """
    Возвращает историю запросов анализа пользователя.

    Новые запросы идут первыми.
    Для каждого запроса возвращается количество дефектов.
    """

    if account_id <= 0:
        raise ValueError("account_id must be positive")

    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")

    if offset < 0:
        raise ValueError("offset must be non-negative")

    # Считаем дефекты отдельно для каждого Analysis.
    detection_counts = (
        select(
            Detection.analysis_id,
            func.count(Detection.detection_id).label(
                "detections_count"
            ),
        )
        .group_by(Detection.analysis_id)
        .subquery()
    )

    statement = (
        select(
            AnalysisRequest,
            Analysis.analysis_id,
            func.coalesce(
                detection_counts.c.detections_count,
                0,
            ).label("detections_count"),
        )
        .outerjoin(
            Analysis,
            Analysis.analysis_request_id
            == AnalysisRequest.analysis_request_id,
        )
        .outerjoin(
            detection_counts,
            detection_counts.c.analysis_id
            == Analysis.analysis_id,
        )
        .where(
            AnalysisRequest.account_id == account_id,
        )
        .order_by(
            AnalysisRequest.created_at.desc(),
            AnalysisRequest.analysis_request_id.desc(),
        )
        .limit(limit)
        .offset(offset)
    )

    rows = db.execute(statement).all()

    history = []

    for request, analysis_id, detections_count in rows:
        history.append(
            {
                "request_id": request.analysis_request_id,
                "image_id": request.image_id,
                "analysis_id": analysis_id,
                "status": request.request_status,
                "created_at": request.created_at,
                "finished_at": request.finished_at,
                "detections_count": int(detections_count),
            }
        )

    return history
