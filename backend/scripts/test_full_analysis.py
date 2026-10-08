import hashlib
import shutil
import uuid
from pathlib import Path

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.analysis_request import AnalysisRequest
from app.models.detection import Detection
from app.repositories.image_repository import (
    create_board_for_upload,
    create_image,
    get_demo_account,
)
from app.services.analysis_request_service import (
    create_analysis_request_for_image,
)
from app.services.image_storage import ImageStorage
from app.services.ml_analysis_service import run_analysis


SOURCE_IMAGE = (
    Path.home()
    / "Desktop/PCB_ML_SOURCE/sample1_input.jpg"
)


def main():
    if not SOURCE_IMAGE.is_file():
        raise FileNotFoundError(SOURCE_IMAGE)

    storage = ImageStorage()

    storage_key = f"test-{uuid.uuid4().hex}.jpg"
    destination = storage.get_path(storage_key)

    shutil.copy2(SOURCE_IMAGE, destination)

    print("Изображение скопировано:", destination)

    try:
        with SessionLocal() as db:
            account = get_demo_account(db)

            board = create_board_for_upload(
                db,
                account_id=account.account_id,
                original_filename=SOURCE_IMAGE.name,
            )

            image = create_image(
                db,
                board_id=board.board_id,
                account_id=account.account_id,
                storage_key=storage_key,
                original_filename=SOURCE_IMAGE.name,
                mime_type="image/jpeg",
                file_size=SOURCE_IMAGE.stat().st_size,
            )

            db.commit()

            image_id = image.image_id

            print("Image ID:", image_id)

            request = create_analysis_request_for_image(
                db,
                image_id,
            )

            request_id = request.analysis_request_id

            print("AnalysisRequest ID:", request_id)
            print("Запускаем YOLOv8...")

            analysis = run_analysis(
                db,
                request_id,
            )

            print("Analysis ID:", analysis.analysis_id)

            request = db.get(
                AnalysisRequest,
                request_id,
            )

            detections = db.scalars(
                select(Detection).where(
                    Detection.analysis_id == analysis.analysis_id
                )
            ).all()

            print("Статус:", request.request_status)
            print("Количество дефектов:", len(detections))

            for detection in detections:
                print(
                    "Detection:",
                    detection.detection_id,
                    "class:",
                    detection.defect_type_id,
                    "confidence:",
                    round(detection.confidence, 4),
                    "bbox:",
                    (
                        detection.bbox_x,
                        detection.bbox_y,
                        detection.bbox_width,
                        detection.bbox_height,
                    ),
                )

            assert request.request_status == "completed"

            print()
            print("СКВОЗНОЙ ТЕСТ УСПЕШНО ПРОЙДЕН")

    except Exception:
        # Если создание записей не удалось, убираем
        # скопированный файл.
        # При ошибке после коммита записи в тестовой БД
        # могут остаться — их очистим отдельно.
        destination.unlink(missing_ok=True)
        raise


if __name__ == "__main__":
    main()
