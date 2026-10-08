from sqlalchemy.orm import Session

from app.exceptions import (
    AnalysisRequestNotFoundError,
    ImageNotFoundError,
    InvalidAnalysisRequestTransitionError,
)
from app.models.analysis_request import AnalysisRequest
from app.repositories.analysis_request_repository import (
    create_analysis_request,
    get_analysis_request,
    mark_failed,
    mark_processing,
)
from app.repositories.image_repository import (
    get_demo_account,
    get_image,
)


def create_analysis_request_for_image(
    db: Session,
    image_id: int,
) -> AnalysisRequest:
    try:
        image = get_image(db, image_id)

        if image is None:
            raise ImageNotFoundError(
                f"Image with id={image_id} was not found."
            )

        account = get_demo_account(db)

        analysis_request = create_analysis_request(
            db=db,
            account_id=account.account_id,
            image_id=image.image_id,
        )

        db.commit()
        db.refresh(analysis_request)

        return analysis_request

    except Exception:
        db.rollback()
        raise


def get_analysis_request_by_id(
    db: Session,
    request_id: int,
) -> AnalysisRequest:
    analysis_request = get_analysis_request(db, request_id)

    if analysis_request is None:
        raise AnalysisRequestNotFoundError(
            f"AnalysisRequest with id={request_id} was not found."
        )

    return analysis_request


def start_processing(
    db: Session,
    request_id: int,
) -> AnalysisRequest:
    try:
        analysis_request = get_analysis_request_by_id(
            db,
            request_id,
        )

        if analysis_request.request_status != "created":
            raise InvalidAnalysisRequestTransitionError(
                "AnalysisRequest can enter processing only from created status."
            )

        mark_processing(db, analysis_request)

        db.commit()
        db.refresh(analysis_request)

        return analysis_request

    except Exception:
        db.rollback()
        raise


def fail_processing(
    db: Session,
    request_id: int,
    *,
    error_code: str,
    error_message: str | None = None,
) -> AnalysisRequest:
    try:
        analysis_request = get_analysis_request_by_id(
            db,
            request_id,
        )

        if analysis_request.request_status != "processing":
            raise InvalidAnalysisRequestTransitionError(
                "AnalysisRequest can enter failed only from processing status."
            )

        if not error_code:
            raise ValueError("error_code must not be empty.")

        mark_failed(
            db,
            analysis_request,
            error_code=error_code,
            error_message=error_message,
        )

        db.commit()
        db.refresh(analysis_request)

        return analysis_request

    except Exception:
        db.rollback()
        raise