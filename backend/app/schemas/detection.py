from pydantic import BaseModel, Field


class BBoxResponse(BaseModel):
    x_min: float = Field(ge=0.0, le=1.0)
    y_min: float = Field(ge=0.0, le=1.0)
    x_max: float = Field(ge=0.0, le=1.0)
    y_max: float = Field(ge=0.0, le=1.0)


class DetectionResponse(BaseModel):
    defect_type: str
    confidence: float = Field(ge=0.0, le=1.0)
    bbox: BBoxResponse
