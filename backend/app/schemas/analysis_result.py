from typing import Literal

from pydantic import BaseModel

from app.schemas.detection import DetectionResponse


class AnalysisResultResponse(BaseModel):
    request_id: int
    image_id: int
    status: Literal["completed"]
    model_version: str
    detections: list[DetectionResponse]
