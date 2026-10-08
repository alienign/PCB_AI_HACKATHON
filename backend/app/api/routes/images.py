from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.repositories.image_repository import get_image
from app.schemas.image import ImageUploadResponse
from app.services.image_storage import ImageStorage
from app.services.image_validation import validate_image
from app.services.upload_service import save_uploaded_image


router = APIRouter(prefix="/images", tags=["images"])


@router.post("", response_model=ImageUploadResponse)
async def upload_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    await validate_image(file)

    image = await save_uploaded_image(
        db=db,
        file=file,
    )

    return ImageUploadResponse(
        image_id=image.image_id,
    )


@router.get("/{image_id}")
def get_uploaded_image(
    image_id: int,
    db: Session = Depends(get_db),
):
    """Возвращает ранее загруженное изображение по image_id."""

    image = get_image(db, image_id)

    if image is None:
        raise HTTPException(
            status_code=404,
            detail="Image not found.",
        )

    storage = ImageStorage()
    image_path = storage.get_path(image.storage_key)

    if not image_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Image file not found.",
        )

    return FileResponse(
        path=image_path,
        media_type=image.mime_type,
    )
