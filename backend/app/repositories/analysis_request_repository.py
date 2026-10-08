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
