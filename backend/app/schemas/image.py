from pydantic import BaseModel


class ImageUploadResponse(BaseModel):
    image_id: int