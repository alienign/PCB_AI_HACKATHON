from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.analysis_request import AnalysisRequest


def create_analysis_request(
    db: Session,
    *,
    account_id: int,
    image_id: int,
) -> AnalysisRequest:
    analysis_request = AnalysisRequest(
        account_id=account_id,
        image_id=image_id,
        request_status="created",
    )

    db.add(analysis_request)
    db.flush()

    return analysis_request


def get_analysis_request(
    db: Session,
    request_id: int,
) -> AnalysisRequest | None:
    return db.get(AnalysisRequest, request_id)


def mark_analysis_processing(
    db: Session,
    analysis_request: AnalysisRequest,
) -> AnalysisRequest:
    if analysis_request.request_status != "created":
        raise ValueError(
            "Only created analysis requests can start processing."
        )

    analysis_request.request_status = "processing"
    analysis_request.started_at = datetime.now(timezone.utc)

    db.flush()

    return analysis_request


def mark_analysis_failed(
    db: Session,
    analysis_request: AnalysisRequest,
    *,
    error_code: str,
    error_message: str,
) -> AnalysisRequest:
    if analysis_request.request_status != "processing":
        raise ValueError(
            "Only processing analysis requests can fail."
        )

    analysis_request.request_status = "failed"
    analysis_request.finished_at = datetime.now(timezone.utc)
    analysis_request.error_code = error_code
    analysis_request.error_message = error_message

    db.flush()

    return analysis_request
