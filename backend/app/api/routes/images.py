from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.schemas.image import ImageUploadResponse
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