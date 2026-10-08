import hashlib
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.model_version import ModelVersion
from app.repositories.model_version_repository import (
    create_model_version,
    get_model_version,
)


MODEL_NAME = "pcb-yolov8m-dspcbsd"
MODEL_VERSION = "v1"


def calculate_sha256(file_path: Path) -> str:
    """Вычисляет SHA-256 файла модели."""

    digest = hashlib.sha256()

    with file_path.open("rb") as file:
        for chunk in iter(
            lambda: file.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def register_ml_model(db: Session) -> ModelVersion:
    """Регистрирует ML-модель в PostgreSQL."""

    model_path = Path(settings.ml_model_path).expanduser()

    if not model_path.is_file():
        raise FileNotFoundError(
            f"ML model not found: {model_path}"
        )

    weights_hash = calculate_sha256(model_path)

    existing = get_model_version(
        db,
        model_name=MODEL_NAME,
        version_name=MODEL_VERSION,
    )

    if existing is not None:
        if existing.weights_hash != weights_hash:
            raise ValueError(
                "Model version already exists with different weights. "
                "Use a new version name."
            )

        return existing

    try:
        model = create_model_version(
            db,
            model_name=MODEL_NAME,
            version_name=MODEL_VERSION,
            weights_hash=weights_hash,
        )

        db.commit()
        db.refresh(model)

        return model

    except Exception:
        db.rollback()
        raise
