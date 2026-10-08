from typing import Literal

from pydantic import BaseModel


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


class AnalysisRequestStatusResponse(BaseModel):
    request_id: int
    status: AnalysisStatus
