from sqlalchemy import func
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


def mark_processing(
    db: Session,
    analysis_request: AnalysisRequest,
) -> AnalysisRequest:
    from sqlalchemy import update

    stmt = (
        update(AnalysisRequest)
        .where(
            AnalysisRequest.analysis_request_id
            == analysis_request.analysis_request_id,
            AnalysisRequest.request_status == "created",
        )
        .values(
            request_status="processing",
            started_at=func.now(),
        )
        .returning(AnalysisRequest.analysis_request_id)
    )

    updated_id = db.scalar(stmt)

    if updated_id is None:
        raise ValueError(
            "Only created analysis requests can start processing."
        )

    db.refresh(analysis_request)

    return analysis_request


def mark_failed(
    db: Session,
    analysis_request: AnalysisRequest,
    *,
    error_code: str,
    error_message: str | None = None,
) -> AnalysisRequest:
    if analysis_request.request_status != "processing":
        raise ValueError(
            "Only processing analysis requests can fail."
        )

    if not error_code:
        raise ValueError("error_code must not be empty.")

    analysis_request.request_status = "failed"
    analysis_request.finished_at = func.now()
    analysis_request.error_code = error_code
    analysis_request.error_message = error_message

    db.flush()

    return analysis_request
