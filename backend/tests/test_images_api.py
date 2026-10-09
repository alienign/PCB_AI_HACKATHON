import asyncio
import os
from io import BytesIO
from unittest.mock import patch

import pytest
from fastapi import UploadFile
from fastapi.testclient import TestClient
from PIL import Image as PILImage
from sqlalchemy import select, text

from app.core.config import settings
from app.db.session import SessionLocal
from app.main import app
from app.models.board import Board
from app.models.image import Image
from app.services.upload_service import save_uploaded_image


TEST_DB = "pcb_ai_test"


@pytest.fixture
def safe_test_environment(tmp_path, monkeypatch):
    """Защита основной БД и отдельное хранилище для тестов."""

    database_url = os.getenv("DATABASE_URL", "")
    test_database_url = os.getenv("TEST_DATABASE_URL", "")

    if not database_url or database_url != test_database_url:
        pytest.fail(
            "DATABASE_URL must match TEST_DATABASE_URL"
        )

    with SessionLocal() as db:
        current_database = db.execute(
            text("SELECT current_database()")
        ).scalar_one()

    if current_database != TEST_DB:
        pytest.fail(
            f"Expected {TEST_DB}, got {current_database}"
        )

    monkeypatch.setattr(
        settings,
        "storage_path",
        str(tmp_path),
    )

    yield tmp_path


@pytest.fixture
def client(safe_test_environment):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def uploaded_images():
    """Удаляет только записи, созданные текущим тестом."""

    created_ids = []

    yield created_ids

    with SessionLocal() as db:
        for image_id in created_ids:
            image = db.get(Image, image_id)

            if image is None:
                continue

            board_id = image.board_id

            db.delete(image)
            db.flush()

            board = db.get(Board, board_id)

            if board is not None:
                db.delete(board)

        db.commit()


def make_image(image_format="PNG"):
    """Создаёт маленькое настоящее изображение."""

    buffer = BytesIO()

    image = PILImage.new(
        "RGB",
        (20, 20),
        color="white",
    )

    image.save(buffer, format=image_format)

    return buffer.getvalue()


@pytest.mark.parametrize(
    "filename,mime_type,image_format",
    [
        ("board.png", "image/png", "PNG"),
        ("board.jpg", "image/jpeg", "JPEG"),
    ],
)
def test_upload_valid_image(
    client,
    safe_test_environment,
    uploaded_images,
    filename,
    mime_type,
    image_format,
):
    response = client.post(
        "/images",
        files={
            "file": (
                filename,
                make_image(image_format),
                mime_type,
            )
        },
    )

    assert response.status_code == 200

    image_id = response.json()["image_id"]
    uploaded_images.append(image_id)

    with SessionLocal() as db:
        image = db.get(Image, image_id)

        assert image is not None
        assert image.mime_type == mime_type

        saved_path = (
            safe_test_environment / image.storage_key
        )

        assert saved_path.exists()


def test_upload_unsupported_format(client):
    response = client.post(
        "/images",
        files={
            "file": (
                "board.gif",
                b"fake gif content",
                "image/gif",
            )
        },
    )

    assert response.status_code == 400


def test_upload_empty_file(client):
    response = client.post(
        "/images",
        files={
            "file": (
                "board.png",
                b"",
                "image/png",
            )
        },
    )

    assert response.status_code == 400


def test_upload_corrupted_image(client):
    response = client.post(
        "/images",
        files={
            "file": (
                "board.png",
                b"not a real image",
                "image/png",
            )
        },
    )

    assert response.status_code == 400


def test_upload_too_large_image(client):
    response = client.post(
        "/images",
        files={
            "file": (
                "board.png",
                b"x" * (10 * 1024 * 1024 + 1),
                "image/png",
            )
        },
    )

    assert response.status_code == 400


@pytest.mark.parametrize(
    "filename,mime_type,image_format",
    [
        ("board.png", "image/png", "PNG"),
        ("board.jpg", "image/jpeg", "JPEG"),
    ],
)
def test_get_uploaded_image(
    client,
    safe_test_environment,
    uploaded_images,
    filename,
    mime_type,
    image_format,
):
    """GET возвращает ранее загруженное изображение."""

    original_content = make_image(image_format)

    upload_response = client.post(
        "/images",
        files={
            "file": (
                filename,
                original_content,
                mime_type,
            )
        },
    )

    assert upload_response.status_code == 200

    image_id = upload_response.json()["image_id"]
    uploaded_images.append(image_id)

    response = client.get(f"/images/{image_id}")

    assert response.status_code == 200
    assert response.headers["content-type"] == mime_type
    assert response.content == original_content


def test_get_unknown_image(client):
    """Несуществующее изображение возвращает 404."""

    response = client.get("/images/999999999")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Image not found."
    }


def test_get_image_missing_file(
    client,
    safe_test_environment,
    uploaded_images,
):
    """Если запись есть, но файл отсутствует, GET возвращает 404."""

    upload_response = client.post(
        "/images",
        files={
            "file": (
                "board.png",
                make_image("PNG"),
                "image/png",
            )
        },
    )

    assert upload_response.status_code == 200

    image_id = upload_response.json()["image_id"]
    uploaded_images.append(image_id)

    with SessionLocal() as db:
        image = db.get(Image, image_id)

        assert image is not None

        file_path = (
            safe_test_environment / image.storage_key
        )

    assert file_path.exists()
    file_path.unlink()

    response = client.get(f"/images/{image_id}")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Image file not found."
    }


def test_upload_does_not_refresh_after_commit(
    safe_test_environment,
    monkeypatch,
):
    """
    Проверяет, что загрузка проходит без db.refresh(image),
    а запись PostgreSQL соответствует сохранённому файлу.
    """

    original_refresh = SessionLocal.class_.refresh

    def broken_refresh(self, instance, *args, **kwargs):
        if isinstance(instance, Image):
            raise RuntimeError(
                "Unexpected image refresh"
            )

        return original_refresh(
            self,
            instance,
            *args,
            **kwargs,
        )

    image_id = None
    board_id = None
    storage_key = None

    # Дополнительная защита: запоминаем файлы до теста.
    initial_files = set(
        safe_test_environment.iterdir()
    )

    try:
        with patch.object(
            SessionLocal.class_,
            "refresh",
            broken_refresh,
        ):
            with SessionLocal() as db:
                file = UploadFile(
                    filename="board.png",
                    file=BytesIO(make_image("PNG")),
                )

                image = asyncio.run(
                    save_uploaded_image(
                        db=db,
                        file=file,
                    )
                )

                image_id = image.image_id
                board_id = image.board_id
                storage_key = image.storage_key

        # Проверяем запись в отдельной сессии PostgreSQL.
        with SessionLocal() as db:
            saved_image = db.get(Image, image_id)

            assert saved_image is not None
            assert saved_image.storage_key == storage_key

        # Проверяем физический файл.
        saved_path = (
            safe_test_environment / storage_key
        )

        assert saved_path.is_file()

        assert saved_path.read_bytes() == make_image(
            "PNG"
        )

    finally:
        # Удаляем только запись, созданную этим тестом.
        if image_id is not None:
            with SessionLocal() as db:
                saved_image = db.get(Image, image_id)

                if saved_image is not None:
                    board_id = saved_image.board_id
                    db.delete(saved_image)
                    db.flush()

                if board_id is not None:
                    board = db.get(Board, board_id)

                    if board is not None:
                        db.delete(board)

                db.commit()

        # Удаляем только файлы из временного хранилища.
        for file_path in safe_test_environment.iterdir():
            if file_path not in initial_files:
                file_path.unlink()


def test_reject_mismatched_image_mime_type(
    client,
    safe_test_environment,
):
    """
    JPEG с заявленным MIME image/png должен отклоняться.

    Проверяем:
    - HTTP 400;
    - корректное сообщение об ошибке;
    - отсутствие новых записей в PostgreSQL;
    - отсутствие новых файлов на диске.

    Если Backend ошибочно примет изображение,
    созданные тестом данные будут удалены.
    """

    from uuid import uuid4

    filename = f"mime_mismatch_{uuid4().hex}.png"

    initial_files = set(safe_test_environment.iterdir())

    created_image_id = None
    created_board_id = None

    try:
        response = client.post(
            "/images",
            files={
                "file": (
                    filename,
                    make_image("JPEG"),
                    "image/png",
                )
            },
        )

        # Если Backend ошибочно принял файл,
        # запоминаем созданные записи для очистки.
        with SessionLocal() as db:
            image = db.scalar(
                select(Image).where(
                    Image.original_filename == filename
                )
            )

            if image is not None:
                created_image_id = image.image_id
                created_board_id = image.board_id

        # JPEG нельзя принимать как PNG.
        assert response.status_code == 400

        assert response.json() == {
            "detail": "Image format does not match MIME type."
        }

        # При отклонении изображения не должно
        # появляться новых записей и файлов.
        assert created_image_id is None

        assert set(safe_test_environment.iterdir()) == initial_files

    finally:
        # Удаляем созданную тестом запись, если она есть.
        with SessionLocal() as db:
            image = db.scalar(
                select(Image).where(
                    Image.original_filename == filename
                )
            )

            if image is not None:
                created_board_id = image.board_id

                db.delete(image)
                db.flush()

            if created_board_id is not None:
                board = db.get(Board, created_board_id)

                if board is not None:
                    db.delete(board)

            db.commit()

        # Удаляем созданные тестом файлы
        # исключительно из временной папки.
        for file_path in safe_test_environment.iterdir():
            if file_path not in initial_files:
                file_path.unlink()
