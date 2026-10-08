from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.analysis_request import AnalysisRequest
from app.repositories.analysis_request_repository import (
    create_analysis_request,
    get_analysis_request,
)
from app.repositories.image_repository import get_demo_account, get_image


def start_analysis(
    db: Session,
    image_id: int,
) -> AnalysisRequest:
    image = get_image(db, image_id)

    if image is None:
        raise HTTPException(
            status_code=404,
            detail="Image not found.",
        )

    account = get_demo_account(db)

    try:
        analysis_request = create_analysis_request(
            db,
            account_id=account.account_id,
            image_id=image.image_id,
        )

        db.commit()
        db.refresh(analysis_request)

        return analysis_request

    except Exception:
        db.rollback()
        raise


def get_analysis_status(
    db: Session,
    request_id: int,
) -> AnalysisRequest:
    analysis_request = get_analysis_request(db, request_id)

    if analysis_request is None:
        raise HTTPException(
            status_code=404,
            detail="Analysis request not found.",
        )

    return analysis_request