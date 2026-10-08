from fastapi import HTTPException
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


# Основная реализация Глеба
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

        # Получаем актуальные значения до фиксации транзакции.
        db.refresh(analysis_request)
        db.commit()

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
                "AnalysisRequest can enter processing "
                "only from created status."
            )

        # Атомарный переход created -> processing.
        # Только один конкурентный запрос может изменить статус.
        try:
            mark_processing(
                db,
                analysis_request,
            )
        except ValueError as error:
            raise InvalidAnalysisRequestTransitionError(
                "AnalysisRequest can enter processing "
                "only from created status."
            ) from error

        # mark_processing уже выполняет db.refresh().
        # Дополнительный refresh после commit не требуется.
        db.commit()

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
                "AnalysisRequest can enter failed "
                "only from processing status."
            )

        if not error_code:
            raise ValueError(
                "error_code must not be empty."
            )

        mark_failed(
            db,
            analysis_request,
            error_code=error_code,
            error_message=error_message,
        )

        # Получаем значения, сформированные PostgreSQL,
        # пока транзакция ещё не зафиксирована.
        db.refresh(analysis_request)
        db.commit()

        return analysis_request

    except Exception:
        db.rollback()
        raise


# Совместимость с существующим API Алины
def start_analysis(
    db: Session,
    image_id: int,
) -> AnalysisRequest:
    try:
        return create_analysis_request_for_image(
            db,
            image_id,
        )
    except ImageNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Image not found.",
        )


def get_analysis_status(
    db: Session,
    request_id: int,
) -> AnalysisRequest:
    try:
        return get_analysis_request_by_id(
            db,
            request_id,
        )
    except AnalysisRequestNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Analysis request not found.",
        )


def begin_analysis_processing(
    db: Session,
    request_id: int,
) -> AnalysisRequest:
    try:
        return start_processing(
            db,
            request_id,
        )
    except AnalysisRequestNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Analysis request not found.",
        )
    except InvalidAnalysisRequestTransitionError:
        raise HTTPException(
            status_code=409,
            detail="Analysis request is not in created status.",
        )