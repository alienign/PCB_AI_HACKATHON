from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.models.image import Image
from app.repositories.image_repository import (
    create_board_for_upload,
    create_image,
    get_demo_account,
)
from app.services.image_storage import ImageStorage


async def save_uploaded_image(
    db: Session,
    file: UploadFile,
) -> Image:
    storage = ImageStorage()

    original_filename = file.filename or "image"
    mime_type = file.content_type or "application/octet-stream"

    storage_key: str | None = None

    try:
        # 1. Получаем demo account из PostgreSQL.
        account = get_demo_account(db)

        # 2. Для каждой загрузки создаём новую Board.
        board = create_board_for_upload(
            db=db,
            account_id=account.account_id,
            original_filename=original_filename,
        )

        # 3. Сохраняем изображение на диск.
        storage_key = await storage.save(file)

        file_path = storage.get_path(storage_key)
        file_size = file_path.stat().st_size

        # 4. Создаём запись Image с настоящими FK.
        image = create_image(
            db=db,
            board_id=board.board_id,
            account_id=account.account_id,
            storage_key=storage_key,
            original_filename=original_filename,
            mime_type=mime_type,
            file_size=file_size,
        )

        # 5. Фиксируем Board и Image одной транзакцией.
        db.commit()

        # db.refresh(image) здесь не нужен:
        # image_id уже получен при db.flush() в create_image(),
        # а SessionLocal настроен с expire_on_commit=False.
        return image

    except Exception:
        # Откатываем незавершённую транзакцию.
        db.rollback()

        # Удаляем сохранённый файл, если операция
        # завершилась ошибкой до успешного commit().
        if storage_key is not None:
            file_path = storage.get_path(storage_key)

            if file_path.exists():
                file_path.unlink()

        raise
