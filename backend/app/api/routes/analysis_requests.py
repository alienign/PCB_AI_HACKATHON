from fastapi import Query

from app.repositories.image_repository import get_demo_account
from app.schemas.analysis_request import AnalysisHistoryItemResponse
from app.services.analysis_history_service import get_analysis_history

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.db.session import SessionLocal

from app.schemas.analysis_request import (
    AnalysisRequestCreate,
    AnalysisRequestCreateResponse,
    AnalysisRequestStatusResponse,
)

from app.services.analysis_request_service import (
    get_analysis_status,
    start_analysis,
)

from app.services.analysis_query_service import get_analysis_result
from app.services.ml_analysis_service import run_analysis


router = APIRouter(
    prefix="/analysis-requests",
    tags=["analysis-requests"],
)


def process_analysis_in_background(request_id: int):
    """Запускает ML-анализ с отдельной сессией PostgreSQL."""
    with SessionLocal() as db:
        run_analysis(db, request_id)


@router.post(
    "",
    response_model=AnalysisRequestCreateResponse,
)
def create_analysis_request(
    payload: AnalysisRequestCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    # Создаём запрос анализа в PostgreSQL.
    analysis_request = start_analysis(
        db=db,
        image_id=payload.image_id,
    )

    # Запускаем обработку изображения в фоне.
    background_tasks.add_task(
        process_analysis_in_background,
        analysis_request.analysis_request_id,
    )

    # Сразу возвращаем идентификатор запроса.
    return AnalysisRequestCreateResponse(
        request_id=analysis_request.analysis_request_id,
        status="created",
    )


@router.get(
    "/{request_id}",
    response_model=AnalysisRequestStatusResponse,
)
def read_analysis_request_status(
    request_id: int,
    db: Session = Depends(get_db),
):
    # Проверяем, что запрос существует.
    get_analysis_status(
        db=db,
        request_id=request_id,
    )

    # Получаем статус и результаты анализа из PostgreSQL.
    result = get_analysis_result(
        db,
        request_id,
    )

    detections = []

    # Преобразуем координаты из формата базы данных
    # в формат, который нужен приложению Насти.
    for detection in result["detections"]:
        bbox = detection["bbox"]

        detections.append(
            {
                "defect_type": detection["defect_code"],
                "confidence": detection["confidence"],
                "bbox": {
                    "x_min": bbox["x"],
                    "y_min": bbox["y"],
                    "x_max": bbox["x"] + bbox["width"],
                    "y_max": bbox["y"] + bbox["height"],
                },
            }
        )

    return AnalysisRequestStatusResponse(
        request_id=result["request_id"],
        status=result["status"],
        detections=detections,
        error_code=result["error_code"],
        error_message=result["error_message"],
    )


@router.get(
    "",
    response_model=list[AnalysisHistoryItemResponse],
)
def read_analysis_history(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """Возвращает историю анализов demo-пользователя."""

    account = get_demo_account(db)

    return get_analysis_history(
        db=db,
        account_id=account.account_id,
        limit=limit,
        offset=offset,
    )