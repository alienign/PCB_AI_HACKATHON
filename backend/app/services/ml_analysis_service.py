from sqlalchemy.orm import Session

from app.models.analysis import Analysis
from app.repositories.image_repository import get_image
from app.services.analysis_request_service import (
    fail_processing,
    get_analysis_request_by_id,
    start_processing,
)
from app.services.analysis_result_service import save_analysis_result
from app.services.image_storage import ImageStorage
from app.services.ml_service import analyze
from app.services.model_registry_service import register_ml_model


def run_analysis(
    db: Session,
    request_id: int,
) -> Analysis:
    """
    Выполняет полный анализ изображения PCB.

    1. Переводит AnalysisRequest в processing.
    2. Получает изображение.
    3. Запускает YOLO.
    4. Регистрирует версию модели.
    5. Сохраняет Analysis и Detection.
    6. Переводит AnalysisRequest в completed.

    При ошибке после перехода в processing
    переводит запрос в failed.
    """

    request = get_analysis_request_by_id(
        db,
        request_id,
    )

    # Проверяем переход created -> processing.
    start_processing(db, request_id)

    try:
        image = get_image(
            db,
            request.image_id,
        )

        if image is None:
            raise ValueError(
                f"Image {request.image_id} not found."
            )

        storage = ImageStorage()

        image_path = storage.get_path(
            image.storage_key,
        )

        # Запускаем нейросеть.
        detections = analyze(image_path)

        # Получаем запись о версии модели.
        model_version = register_ml_model(db)

        # Сохраняем результат и завершаем запрос.
        analysis = save_analysis_result(
            db,
            request_id=request_id,
            model_version_id=model_version.model_version_id,
            detections=detections,
        )

        return analysis

    except Exception as error:
        db.rollback()

        # Сохраняем информацию об ошибке.
        fail_processing(
            db,
            request_id,
            error_code="ANALYSIS_FAILED",
            error_message=str(error)[:1000],
        )

        raise
