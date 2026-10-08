from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.schemas.analysis_request import (
    AnalysisRequestCreate,
    AnalysisRequestCreateResponse,
)
from app.services.analysis_request_service import start_analysis


router = APIRouter(
    prefix="/analysis-requests",
    tags=["analysis-requests"],
)


@router.post("", response_model=AnalysisRequestCreateResponse)
def create_analysis_request(
    payload: AnalysisRequestCreate,
    db: Session = Depends(get_db),
):
    analysis_request = start_analysis(
        db=db,
        image_id=payload.image_id,
    )

    return AnalysisRequestCreateResponse(
        request_id=analysis_request.analysis_request_id,
        status="created",
    )
