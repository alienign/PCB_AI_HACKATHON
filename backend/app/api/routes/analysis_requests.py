from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.schemas.analysis_request import (
    AnalysisRequestCreate,
    AnalysisRequestCreateResponse,
    AnalysisRequestStatusResponse,
)
from app.services.analysis_request_service import (
    get_analysis_status,
    start_analysis,
)


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


@router.get(
    "/{request_id}",
    response_model=AnalysisRequestStatusResponse,
)
def read_analysis_request_status(
    request_id: int,
    db: Session = Depends(get_db),
):
    analysis_request = get_analysis_status(
        db=db,
        request_id=request_id,
    )

    return AnalysisRequestStatusResponse(
        request_id=analysis_request.analysis_request_id,
        status=analysis_request.request_status,
    )
