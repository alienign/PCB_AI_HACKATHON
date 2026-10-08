from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.model_version import ModelVersion


def get_model_version(
    db: Session,
    *,
    model_name: str,
    version_name: str,
) -> ModelVersion | None:
    statement = select(ModelVersion).where(
        ModelVersion.model_name == model_name,
        ModelVersion.version_name == version_name,
    )

    return db.scalar(statement)


def create_model_version(
    db: Session,
    *,
    model_name: str,
    version_name: str,
    weights_hash: str | None = None,
) -> ModelVersion:
    model_version = ModelVersion(
        model_name=model_name,
        version_name=version_name,
        weights_hash=weights_hash,
    )

    db.add(model_version)
    db.flush()

    return model_version