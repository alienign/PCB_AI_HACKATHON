import os
from uuid import uuid4
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from app.main import app
from app.db.session import SessionLocal
from app.models.account import Account
from app.models.board import Board
from app.models.image import Image
from app.models.analysis_request import AnalysisRequest


TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "")
DATABASE_URL = os.getenv("DATABASE_URL", "")

# Защита от случайного запуска тестов на основной базе.
if not TEST_DATABASE_URL or not DATABASE_URL:
    pytest.skip(
        "DATABASE_URL and TEST_DATABASE_URL are required",
        allow_module_level=True,
    )

if DATABASE_URL != TEST_DATABASE_URL:
    pytest.skip(
        "DATABASE_URL must match TEST_DATABASE_URL",
        allow_module_level=True,
    )

# Проверяем реальное имя базы, а не только строку подключения.
with SessionLocal() as session:
    database_name = session.execute(
        text("SELECT current_database()")
    ).scalar_one()

if database_name != "pcb_ai_test":
    pytest.skip(
        "HTTP integration tests require pcb_ai_test",
        allow_module_level=True,
    )


@pytest.fixture
def client():
    """Создаёт тестовый HTTP-клиент FastAPI."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def test_image():
    """Создаёт временную плату и изображение в тестовой базе."""

    image_id = None
    board_id = None

    with SessionLocal() as db:
        account = db.scalar(
            select(Account).where(
                Account.login == "demo",
                Account.is_active.is_(True),
            )
        )

        assert account is not None, "Demo account not found"

        board = Board(
            created_by_account_id=account.account_id,
            board_label=f"http-api-test-{uuid4()}",
        )

        db.add(board)
        db.flush()

        board_id = board.board_id

        image = Image(
            board_id=board_id,
            uploaded_by_account_id=account.account_id,
            storage_key=f"http-test/{uuid4()}.jpg",
            original_filename="test.jpg",
            mime_type="image/jpeg",
        )

        db.add(image)
        db.flush()

        image_id = image.image_id

        db.commit()

    try:
        yield image_id

    finally:
        # Удаляем только записи, созданные этим тестом.
        with SessionLocal() as db:
            db.query(AnalysisRequest).filter(
                AnalysisRequest.image_id == image_id
            ).delete(synchronize_session=False)

            image = db.get(Image, image_id)

            if image is not None:
                db.delete(image)
                db.flush()

            board = db.get(Board, board_id)

            if board is not None:
                db.delete(board)

            db.commit()


def test_post_analysis_request(client, test_image):
    """POST создаёт запрос и вызывает фоновую задачу."""

    with patch(
        "app.api.routes.analysis_requests."
        "process_analysis_in_background"
    ) as mocked_background:

        response = client.post(
            "/analysis-requests",
            json={"image_id": test_image},
        )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "created"
    assert isinstance(data["request_id"], int)

    mocked_background.assert_called_once_with(
        data["request_id"]
    )


def test_get_analysis_request(client, test_image):
    """GET возвращает существующий запрос."""

    with patch(
        "app.api.routes.analysis_requests."
        "process_analysis_in_background"
    ):
        created = client.post(
            "/analysis-requests",
            json={"image_id": test_image},
        )

    assert created.status_code == 200

    request_id = created.json()["request_id"]

    response = client.get(
        f"/analysis-requests/{request_id}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["request_id"] == request_id
    assert data["status"] == "created"
    assert data["detections"] == []


def test_get_unknown_request(client):
    """Несуществующий запрос возвращает 404."""

    response = client.get(
        "/analysis-requests/999999999"
    )

    assert response.status_code == 404


def test_post_unknown_image(client):
    """Несуществующее изображение возвращает 404."""

    response = client.post(
        "/analysis-requests",
        json={"image_id": 999999999},
    )

    assert response.status_code == 404


def test_post_invalid_body(client):
    """Некорректное тело запроса возвращает 422."""

    response = client.post(
        "/analysis-requests",
        json={},
    )

    assert response.status_code == 422


def test_analysis_history(client):
    """GET истории возвращает список анализов."""

    response = client.get(
        "/analysis-requests?limit=20&offset=0"
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_history_pagination(client):
    """Проверяем пагинацию истории."""

    first_page = client.get(
        "/analysis-requests?limit=1&offset=0"
    )

    second_page = client.get(
        "/analysis-requests?limit=1&offset=1"
    )

    assert first_page.status_code == 200
    assert second_page.status_code == 200

    assert len(first_page.json()) <= 1
    assert len(second_page.json()) <= 1

    if first_page.json() and second_page.json():
        assert (
            first_page.json()[0]["request_id"]
            != second_page.json()[0]["request_id"]
        )


def test_history_invalid_limit(client):
    """Некорректный limit возвращает 422."""

    response = client.get(
        "/analysis-requests?limit=0"
    )

    assert response.status_code == 422


def test_history_invalid_offset(client):
    """Отрицательный offset возвращает 422."""

    response = client.get(
        "/analysis-requests?offset=-1"
    )

    assert response.status_code == 422