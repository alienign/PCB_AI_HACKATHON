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



@pytest.fixture
def db(safe_test_db):
    """Используем только проверенную тестовую БД."""
    yield safe_test_db



@pytest.fixture
def analysis_request_data(db):
    """Создаёт тестовый запрос анализа без сохранения изменений в БД."""
    from uuid import uuid4

    from app.models.account import Account
    from app.models.board import Board
    from app.models.image import Image

    suffix = uuid4().hex

    account = Account(
        login=f"query_test_{suffix}",
        display_name="Query Test",
    )
    db.add(account)
    db.flush()

    board = Board(
        created_by_account_id=account.account_id,
        board_label=f"query-board-{suffix}",
    )
    db.add(board)
    db.flush()

    image = Image(
        board_id=board.board_id,
        uploaded_by_account_id=account.account_id,
        storage_key=f"query-test/{suffix}.jpg",
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

    return request


@pytest.fixture
def completed_analysis_data(db, analysis_request_data):
    """Создаёт завершённый анализ с одним обнаруженным дефектом."""
    from datetime import datetime, timedelta, timezone
    from uuid import uuid4

    suffix = uuid4().hex
    request = analysis_request_data

    model = ModelVersion(
        model_name=f"pytest_model_{suffix}",
        version_name="1.0",
    )
    db.add(model)
    db.flush()

    defect_type = DefectType(
        defect_code=f"pytest_defect_{suffix}",
        defect_name="Test Defect",
    )
    db.add(defect_type)
    db.flush()

    now = datetime.now(timezone.utc)
    request.request_status = "completed"
    request.started_at = now
    request.finished_at = now + timedelta(seconds=1)
    db.flush()

    analysis = Analysis(
        analysis_request_id=request.analysis_request_id,
        model_version_id=model.model_version_id,
    )
    db.add(analysis)
    db.flush()

    detection = Detection(
        analysis_id=analysis.analysis_id,
        defect_type_id=defect_type.defect_type_id,
        confidence=0.95,
        bbox_x=0.1,
        bbox_y=0.2,
        bbox_width=0.3,
        bbox_height=0.4,
    )
    db.add(detection)
    db.flush()

    return request

def test_completed_analysis_with_detections(db, completed_analysis_data):
    """Проверяем результат завершённого анализа с дефектом."""
    request = completed_analysis_data

    result = get_analysis_result(
        db,
        request.analysis_request_id,
    )

    assert result is not None
    assert result["status"] == "completed"
    assert result["analysis_id"] is not None
    assert result["model"] is not None
    assert result["detections_count"] == 1
    assert len(result["detections"]) == 1

    detection = result["detections"][0]

    assert detection["defect_code"]
    assert 0 <= detection["confidence"] <= 1

    bbox = detection["bbox"]

    assert 0 <= bbox["x"] <= 1
    assert 0 <= bbox["y"] <= 1
    assert 0 < bbox["width"] <= 1
    assert 0 < bbox["height"] <= 1


def test_created_request_without_results(db, analysis_request_data):
    """Новый запрос без результатов анализа."""
    request = analysis_request_data

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
