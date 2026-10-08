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
)
from app.services.ml_analysis_service import run_analysis
from app.services.ml_service import MLDetection

import app.services.ml_analysis_service as ml_module


TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

if not TEST_DATABASE_URL:
    pytest.skip(
        "TEST_DATABASE_URL is required",
        allow_module_level=True,
    )


engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)

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

        image_ids = select(Image.image_id).where(
            Image.storage_key.like("pytest-pipeline/%")
        )

        request_ids = select(
            AnalysisRequest.analysis_request_id
        ).where(
            AnalysisRequest.image_id.in_(image_ids)
        )

        analysis_ids = select(
            Analysis.analysis_id
        ).where(
            Analysis.analysis_request_id.in_(request_ids)
        )

        session.query(Detection).filter(
            Detection.analysis_id.in_(analysis_ids)
        ).delete(synchronize_session=False)

        session.query(Analysis).filter(
            Analysis.analysis_request_id.in_(request_ids)
        ).delete(synchronize_session=False)

        session.query(AnalysisRequest).filter(
            AnalysisRequest.image_id.in_(image_ids)
        ).delete(synchronize_session=False)

        session.query(Image).filter(
            Image.storage_key.like("pytest-pipeline/%")
        ).delete(synchronize_session=False)

        session.query(Board).filter(
            Board.board_label == "pytest-pipeline-board"
        ).delete(synchronize_session=False)

        session.query(ModelVersion).filter(
            ModelVersion.model_name == "pytest-pipeline-model"
        ).delete(synchronize_session=False)

        session.commit()
        session.close()


def create_request(db):
    account = db.scalar(
        select(Account).where(
            Account.login == "demo",
            Account.is_active.is_(True),
        )
    )

    assert account is not None

    board = Board(
        created_by_account_id=account.account_id,
        board_label="pytest-pipeline-board",
    )

    db.add(board)
    db.flush()

    image = Image(
        board_id=board.board_id,
        uploaded_by_account_id=account.account_id,
        storage_key=f"pytest-pipeline/{uuid4()}.jpg",
        original_filename="test.jpg",
        mime_type="image/jpeg",
        file_size=123,
    )

    db.add(image)
    db.commit()
    db.refresh(image)

    return create_analysis_request_for_image(
        db,
        image.image_id,
    )


def fake_model_version(db):
    model = ModelVersion(
        model_name="pytest-pipeline-model",
        version_name=str(uuid4()),
    )

    db.add(model)
    db.commit()
    db.refresh(model)

    return model


def make_detection():
    return MLDetection(
        class_id=0,
        defect_code="short",
        confidence=0.95,
        x_min=0.1,
        y_min=0.2,
        x_max=0.4,
        y_max=0.6,
    )


def patch_model(monkeypatch, model):
    monkeypatch.setattr(
        ml_module,
        "register_ml_model",
        lambda db: model,
    )


def test_successful_analysis(db, monkeypatch):
    request = create_request(db)
    model = fake_model_version(db)

    patch_model(monkeypatch, model)

    monkeypatch.setattr(
        ml_module,
        "analyze",
        lambda path: [make_detection(), make_detection()],
    )

    analysis = run_analysis(
        db,
        request.analysis_request_id,
    )

    db.refresh(request)

    assert request.request_status == "completed"
    assert analysis.model_version_id == model.model_version_id

    detections = db.scalars(
        select(Detection).where(
            Detection.analysis_id == analysis.analysis_id
        )
    ).all()

    assert len(detections) == 2


def test_zero_detections(db, monkeypatch):
    request = create_request(db)
    model = fake_model_version(db)

    patch_model(monkeypatch, model)

    monkeypatch.setattr(
        ml_module,
        "analyze",
        lambda path: [],
    )

    analysis = run_analysis(
        db,
        request.analysis_request_id,
    )

    db.refresh(request)

    assert request.request_status == "completed"

    detections = db.scalars(
        select(Detection).where(
            Detection.analysis_id == analysis.analysis_id
        )
    ).all()

    assert detections == []


def test_ml_failure(db, monkeypatch):
    request = create_request(db)

    def broken_analyze(path):
        raise RuntimeError("YOLO inference failed")

    monkeypatch.setattr(
        ml_module,
        "analyze",
        broken_analyze,
    )

    with pytest.raises(
        RuntimeError,
        match="YOLO inference failed",
    ):
        run_analysis(
            db,
            request.analysis_request_id,
        )

    db.refresh(request)

    assert request.request_status == "failed"
    assert request.error_code == "ANALYSIS_FAILED"

    analysis = db.scalar(
        select(Analysis).where(
            Analysis.analysis_request_id
            == request.analysis_request_id
        )
    )

    assert analysis is None


def test_invalid_detection_rolls_back(db, monkeypatch):
    request = create_request(db)
    model = fake_model_version(db)

    patch_model(monkeypatch, model)

    invalid_detection = MLDetection(
        class_id=999,
        defect_code="unknown_defect",
        confidence=0.9,
        x_min=0.1,
        y_min=0.1,
        x_max=0.3,
        y_max=0.3,
    )

    monkeypatch.setattr(
        ml_module,
        "analyze",
        lambda path: [make_detection(), invalid_detection],
    )

    with pytest.raises(
        ValueError,
        match="Unknown defect type",
    ):
        run_analysis(
            db,
            request.analysis_request_id,
        )

    db.refresh(request)

    assert request.request_status == "failed"

    analysis = db.scalar(
        select(Analysis).where(
            Analysis.analysis_request_id
            == request.analysis_request_id
        )
    )

    assert analysis is None


def test_duplicate_analysis_rejected(db, monkeypatch):
    request = create_request(db)
    model = fake_model_version(db)

    patch_model(monkeypatch, model)

    monkeypatch.setattr(
        ml_module,
        "analyze",
        lambda path: [],
    )

    run_analysis(
        db,
        request.analysis_request_id,
    )

    with pytest.raises(Exception):
        run_analysis(
            db,
            request.analysis_request_id,
        )

    db.refresh(request)

    assert request.request_status == "completed"


def test_missing_image_file_marks_request_failed(
    db,
    monkeypatch,
    tmp_path,
):
    """
    Если изображение отсутствует на диске:
    - анализ завершается ошибкой;
    - запрос получает статус failed;
    - запись Analysis не создаётся.
    """
    from app.services.ml_service import PCBDefectModel

    request = create_request(db)

    missing_path = tmp_path / "missing_image.jpg"

    class FakeStorage:
        def get_path(self, storage_key):
            return missing_path

    monkeypatch.setattr(
        ml_module,
        "ImageStorage",
        lambda: FakeStorage(),
    )

    # Не загружаем YOLO: проверяем непосредственно
    # существующую логику проверки файла.
    model = object.__new__(PCBDefectModel)

    monkeypatch.setattr(
        ml_module,
        "analyze",
        lambda path: model.predict(path),
    )

    with pytest.raises(
        FileNotFoundError,
        match="Image not found",
    ):
        run_analysis(
            db,
            request.analysis_request_id,
        )

    db.refresh(request)

    assert request.request_status == "failed"
    assert request.error_code == "ANALYSIS_FAILED"
    assert "Image not found" in request.error_message

    analysis = db.scalar(
        select(Analysis).where(
            Analysis.analysis_request_id
            == request.analysis_request_id
        )
    )

    assert analysis is None


def test_corrupted_image_marks_request_failed(
    db,
    monkeypatch,
    tmp_path,
):
    """
    Повреждённое изображение:
    - существует на диске;
    - не может быть декодировано;
    - переводит запрос в failed;
    - не создаёт Analysis.
    """
    from PIL import Image as PILImage
    from PIL import UnidentifiedImageError

    request = create_request(db)

    corrupted_path = tmp_path / "corrupted.jpg"
    corrupted_path.write_bytes(
        b"this is not a valid JPEG image"
    )

    class FakeStorage:
        def get_path(self, storage_key):
            return corrupted_path

    monkeypatch.setattr(
        ml_module,
        "ImageStorage",
        lambda: FakeStorage(),
    )

    def analyze_corrupted_image(path):
        with PILImage.open(path) as image:
            image.verify()
        return []

    monkeypatch.setattr(
        ml_module,
        "analyze",
        analyze_corrupted_image,
    )

    with pytest.raises(UnidentifiedImageError):
        run_analysis(
            db,
            request.analysis_request_id,
        )

    db.refresh(request)

    assert request.request_status == "failed"
    assert request.error_code == "ANALYSIS_FAILED"

    analysis = db.scalar(
        select(Analysis).where(
            Analysis.analysis_request_id
            == request.analysis_request_id
        )
    )

    assert analysis is None
