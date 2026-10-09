from io import BytesIO

from fastapi import HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError


ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
}

MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB

IMAGE_FORMAT_TO_MIME = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
}


async def validate_image(file: UploadFile) -> None:
    # Проверяем заявленный MIME-тип.
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Unsupported image format. Use JPEG or PNG.",
        )

    # Читаем содержимое файла.
    contents = await file.read()

    if not contents:
        raise HTTPException(
            status_code=400,
            detail="Image file is empty.",
        )

    if len(contents) > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=400,
            detail="Image is too large. Maximum size is 10 MB.",
        )

    try:
        with Image.open(BytesIO(contents)) as image:
            # Определяем настоящий формат изображения.
            actual_format = image.format

            # Проверяем целостность файла.
            image.verify()

    except (UnidentifiedImageError, OSError):
        raise HTTPException(
            status_code=400,
            detail="Invalid or corrupted image file.",
        )

    # Сопоставляем реальный формат с MIME-типом.
    actual_mime_type = IMAGE_FORMAT_TO_MIME.get(actual_format)

    if actual_mime_type != file.content_type:
        raise HTTPException(
            status_code=400,
            detail="Image format does not match MIME type.",
        )

    # Возвращаем указатель чтения в начало,
    # чтобы upload_service сохранил весь файл.
    await file.seek(0)
