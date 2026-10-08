import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.models.account import Account
from app.models.analysis import Analysis
from app.models.analysis_request import AnalysisRequest
from app.models.board import Board
from app.models.detection import Detection
from app.models.image import Image
from app.models.model_version import ModelVersion

from app.services.analysis_request_service import (
    create_analysis_request_for_image,
    start_processing,
)
from app.services.analysis_result_service import save_analysis_result
from app.services.ml_service import MLDetection


TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

if not TEST_DATABASE_URL:
    pytest.skip(
        "TEST_DATABASE_URL is required",
        allow_module_level=True,
    )


engine = create_engine(
    TEST_DATABASE_URL,
    pool_pre_ping=True,
)

TestSessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


@pytest.fixture
def db():
    session = TestSessionLocal()

    try:
        yield session

    finally:
        session.rollback()

        # Удаляем только записи, созданные этими тестами.
        test_image_ids = select(Image.image_id).where(
            Image.storage_key.like("pytest-result/%")
        )

        test_request_ids = select(
            AnalysisRequest.analysis_request_id
        ).where(
            AnalysisRequest.image_id.in_(test_image_ids)
        )

        test_analysis_ids = select(
            Analysis.analysis_id
        ).where(
            Analysis.analysis_request_id.in_(test_request_ids)
        )

        session.query(Detection).filter(
            Detection.analysis_id.in_(test_analysis_ids)
        ).delete(synchronize_session=False)

        session.query(Analysis).filter(
            Analysis.analysis_request_id.in_(test_request_ids)
        ).delete(synchronize_session=False)

        session.query(AnalysisRequest).filter(
            AnalysisRequest.image_id.in_(test_image_ids)
        ).delete(synchronize_session=False)

        session.query(Image).filter(
            Image.storage_key.like("pytest-result/%")
        ).delete(synchronize_session=False)

        session.query(Board).filter(
            Board.board_label == "pytest-result-board"
        ).delete(synchronize_session=False)

        session.query(ModelVersion).filter(
            ModelVersion.model_name == "pytest-result-model"
        ).delete(synchronize_session=False)

        session.commit()
        session.close()


def create_test_image(session):
    account = session.scalar(
        select(Account).where(
            Account.login == "demo",
            Account.is_active.is_(True),
        )
    )

    assert account is not None

    board = Board(
        created_by_account_id=account.account_id,
        board_label="pytest-result-board",
    )

    session.add(board)
    session.flush()

    image = Image(
        board_id=board.board_id,
        uploaded_by_account_id=account.account_id,
        storage_key=f"pytest-result/{uuid4()}.jpg",
        original_filename="test.jpg",
        mime_type="image/jpeg",
        file_size=123,
    )

    session.add(image)
    session.commit()
    session.refresh(image)

    return image


def create_test_model_version(session):
    model = ModelVersion(
        model_name="pytest-result-model",
        version_name=str(uuid4()),
    )

    session.add(model)
    session.commit()
    session.refresh(model)

    return model


def create_processing_request(session):
    image = create_test_image(session)

    request = create_analysis_request_for_image(
        session,
        image.image_id,
    )

    return start_processing(
        session,
        request.analysis_request_id,
    )


def make_detection(
    defect_code="short",
    confidence=0.9,
    x_min=0.1,
    y_min=0.2,
    x_max=0.4,
    y_max=0.6,
):
    return MLDetection(
        class_id=0,
        defect_code=defect_code,
        confidence=confidence,
        x_min=x_min,
        y_min=y_min,
        x_max=x_max,
        y_max=y_max,
    )


def test_zero_detections(db):
    request = create_processing_request(db)
    model = create_test_model_version(db)

    analysis = save_analysis_result(
        db,
        request_id=request.analysis_request_id,
        model_version_id=model.model_version_id,
        detections=[],
    )

    assert analysis.analysis_id is not None

    stored_request = db.get(
        AnalysisRequest,
        request.analysis_request_id,
    )

    assert stored_request.request_status == "completed"
    assert stored_request.finished_at is not None

    detections = db.scalars(
        select(Detection).where(
            Detection.analysis_id == analysis.analysis_id
        )
    ).all()

    assert detections == []


def test_one_detection(db):
    request = create_processing_request(db)
    model = create_test_model_version(db)

    analysis = save_analysis_result(
        db,
        request_id=request.analysis_request_id,
        model_version_id=model.model_version_id,
        detections=[make_detection()],
    )

    detections = db.scalars(
        select(Detection).where(
            Detection.analysis_id == analysis.analysis_id
        )
    ).all()

    assert len(detections) == 1

    detection = detections[0]

    assert detection.confidence == pytest.approx(0.9)
    assert detection.bbox_x == pytest.approx(0.1)
    assert detection.bbox_y == pytest.approx(0.2)
    assert detection.bbox_width == pytest.approx(0.3)
    assert detection.bbox_height == pytest.approx(0.4)


def test_multiple_detections(db):
    request = create_processing_request(db)
    model = create_test_model_version(db)

    analysis = save_analysis_result(
        db,
        request_id=request.analysis_request_id,
        model_version_id=model.model_version_id,
        detections=[
            make_detection("short"),
            make_detection("spur"),
            make_detection("open"),
        ],
    )

    detections = db.scalars(
        select(Detection).where(
            Detection.analysis_id == analysis.analysis_id
        )
    ).all()

    assert len(detections) == 3


def test_unknown_defect_rolls_back(db):
    request = create_processing_request(db)
    model = create_test_model_version(db)

    with pytest.raises(ValueError):
        save_analysis_result(
            db,
            request_id=request.analysis_request_id,
            model_version_id=model.model_version_id,
            detections=[
                make_detection("short"),
                make_detection("unknown_defect"),
            ],
        )

    stored_request = db.get(
        AnalysisRequest,
        request.analysis_request_id,
    )

    assert stored_request.request_status == "processing"

    analysis = db.scalar(
        select(Analysis).where(
            Analysis.analysis_request_id
            == request.analysis_request_id
        )
    )

    assert analysis is None


def test_duplicate_completion_rejected(db):
    request = create_processing_request(db)
    model = create_test_model_version(db)

    save_analysis_result(
        db,
        request_id=request.analysis_request_id,
        model_version_id=model.model_version_id,
        detections=[],
    )

    with pytest.raises(ValueError):
        save_analysis_result(
            db,
            request_id=request.analysis_request_id,
            model_version_id=model.model_version_id,
            detections=[],
        )

    analyses = db.scalars(
        select(Analysis).where(
            Analysis.analysis_request_id
            == request.analysis_request_id
        )
    ).all()

    assert len(analyses) == 1