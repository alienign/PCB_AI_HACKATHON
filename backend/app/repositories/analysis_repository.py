from sqlalchemy.orm import Session

from app.models.analysis import Analysis


def create_analysis(
    db: Session,
    *,
    analysis_request_id: int,
    model_version_id: int,
) -> Analysis:
    analysis = Analysis(
        analysis_request_id=analysis_request_id,
        model_version_id=model_version_id,
    )

    db.add(analysis)
    db.flush()

    return analysis


def get_analysis_by_request_id(
    db: Session,
    request_id: int,
) -> Analysis | None:
    return (
        db.query(Analysis)
        .filter(Analysis.analysis_request_id == request_id)
        .one_or_none()
    )