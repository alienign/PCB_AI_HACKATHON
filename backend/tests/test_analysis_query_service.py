import os

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.models.analysis import Analysis
from app.models.analysis_request import AnalysisRequest
from app.models.defect_type import DefectType
from app.models.detection import Detection
from app.models.model_version import ModelVersion
from app.services.analysis_query_service import get_analysis_result


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
        session.close()


def test_completed_analysis_with_detections(db):
    """
    Проверяем чтение существующего завершённого анализа.
    Используем результаты ранее выполненного сквозного теста.
    """

    request = db.scalar(
        select(AnalysisRequest)
        .where(AnalysisRequest.request_status == "completed")
        .join(
            Analysis,
            Analysis.analysis_request_id
            == AnalysisRequest.analysis_request_id,
        )
        .join(
            Detection,
            Detection.analysis_id == Analysis.analysis_id,
        )
        .limit(1)
    )

    if request is None:
        pytest.skip("No completed analysis with detections")

    result = get_analysis_result(
        db,
        request.analysis_request_id,
    )

    assert result is not None
    assert result["status"] == "completed"
    assert result["analysis_id"] is not None
    assert result["model"] is not None
    assert result["detections_count"] > 0

    for detection in result["detections"]:
        assert detection["defect_code"]
        assert 0 <= detection["confidence"] <= 1

        bbox = detection["bbox"]

        assert 0 <= bbox["x"] <= 1
        assert 0 <= bbox["y"] <= 1
        assert 0 < bbox["width"] <= 1
        assert 0 < bbox["height"] <= 1


def test_created_request_without_results(db):
    """
    Проверяем новый запрос, анализ которого ещё не начался.
    Тест самостоятельно создаёт необходимые записи.
    """
    from uuid import uuid4

    from app.models.account import Account
    from app.models.board import Board
    from app.models.image import Image

    account = db.scalar(
        select(Account).where(
            Account.login == "demo",
            Account.is_active.is_(True),
        )
    )

    assert account is not None

    board = Board(
        created_by_account_id=account.account_id,
        board_label="pytest-query-board",
    )

    db.add(board)
    db.flush()

    image = Image(
        board_id=board.board_id,
        uploaded_by_account_id=account.account_id,
        storage_key=f"pytest-query/{uuid4()}.jpg",
        original_filename="test.jpg",
        mime_type="image/jpeg",
        file_size=123,
    )

    db.add(image)
    db.flush()

    request = AnalysisRequest(
        account_id=account.account_id,
        image_id=image.image_id,
        request_status="created",
    )

    db.add(request)
    db.flush()

    result = get_analysis_result(
        db,
        request.analysis_request_id,
    )

    assert result is not None
    assert result["status"] == "created"
    assert result["analysis_id"] is None
    assert result["model"] is None
    assert result["detections_count"] == 0
    assert result["detections"] == []

    # Откатываем тестовые данные.
    db.rollback()


def test_nonexistent_request(db):
    """
    Несуществующий запрос должен возвращать None.
    """

    max_id = db.scalar(
        select(AnalysisRequest.analysis_request_id)
        .order_by(
            AnalysisRequest.analysis_request_id.desc()
        )
        .limit(1)
    )

    nonexistent_id = (max_id or 0) + 1000000

    result = get_analysis_result(
        db,
        nonexistent_id,
    )

    assert result is None
