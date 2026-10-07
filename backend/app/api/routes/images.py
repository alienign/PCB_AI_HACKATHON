from fastapi import APIRouter, UploadFile, File

from app.schemas.image import ImageUploadResponse
from app.services.image_validation import validate_image


router = APIRouter(
    prefix="/images",
    tags=["images"],
)


@router.post("", response_model=ImageUploadResponse)
async def upload_image(
    file: UploadFile = File(...),
):
    await validate_image(file)

    return ImageUploadResponse(image_id=1)