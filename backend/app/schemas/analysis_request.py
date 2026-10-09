from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class AnalysisRequestCreate(BaseModel):
    image_id: int


class AnalysisRequestCreateResponse(BaseModel):
    request_id: int
    status: Literal["created"]


AnalysisStatus = Literal[
    "created",
    "processing",
    "completed",
    "failed",
]


class BoundingBoxResponse(BaseModel):
    x_min: float
    y_min: float
    x_max: float
    y_max: float


class DetectionResponse(BaseModel):
    defect_type: str
    confidence: float
    bbox: BoundingBoxResponse


class AnalysisRequestStatusResponse(BaseModel):
    request_id: int
    status: AnalysisStatus
    detections: list[DetectionResponse] = Field(default_factory=list)
    error_code: str | None = None
    error_message: str | None = None


class AnalysisHistoryItemResponse(BaseModel):
    request_id: int
    image_id: int
    analysis_id: int | None
    status: AnalysisStatus
    created_at: datetime
    finished_at: datetime | None
    detections_count: int