from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import settings


class ImageStorage:
    def __init__(self, storage_path: str | None = None):
        self.storage_path = Path(storage_path or settings.storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    async def save(self, file: UploadFile) -> str:
        extension = Path(file.filename or "").suffix.lower()

        storage_key = f"{uuid4().hex}{extension}"
        destination = self.storage_path / storage_key

        try:
            await file.seek(0)
            content = await file.read()

            destination.write_bytes(content)

            return storage_key

        except Exception:
            # Удаляем частично записанный файл при ошибке.
            destination.unlink(missing_ok=True)
            raise

    def get_path(self, storage_key: str) -> Path:
        return self.storage_path / storage_key
