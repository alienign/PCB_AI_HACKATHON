import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.exceptions import (
    ImageNotFoundError,
    InvalidAnalysisRequestTransitionError,
)
from app.models.account import Account
from app.models.analysis_request import AnalysisRequest
from app.models.board import Board
from app.models.image import Image
from app.services.analysis_request_service import (
    create_analysis_request_for_image,
    fail_processing,
    start_processing,
)
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier


TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

if not TEST_DATABASE_URL:
    pytest.skip(
        "TEST_DATABASE_URL is required for persistence tests",
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
    """
    Создаёт отдельную SQLAlchemy-сессию для каждого теста.

    После теста удаляются только данные, специально созданные pytest:
    AnalysisRequest -> Image -> Board.

    Demo account и справочник defect_types не удаляются.
    """
    session = TestSessionLocal()

    try:
        yield session

    finally:
        session.rollback()

        # Сначала удаляем AnalysisRequest, потому что они ссылаются на Image.
        session.query(AnalysisRequest).filter(
            AnalysisRequest.image_id.in_(
                select(Image.image_id).where(
                    Image.storage_key.like("pytest/%")
                )
            )
        ).delete(synchronize_session=False)

        # Затем можно удалить изображения.
        session.query(Image).filter(
            Image.storage_key.like("pytest/%")
        ).delete(synchronize_session=False)

        # И только после Image удаляем Board.
        session.query(Board).filter(
            Board.board_label == "pytest-board"
        ).delete(synchronize_session=False)

        session.commit()
        session.close()


def create_test_image(session):
    """
    Создаёт временные Board и Image для конкретного теста.
    Каждое изображение получает уникальный storage_key.
    """
    demo_account = session.scalar(
        select(Account).where(
            Account.login == "demo",
            Account.is_active.is_(True),
        )
    )

    assert demo_account is not None

    board = Board(
        created_by_account_id=demo_account.account_id,
        board_label="pytest-board",
    )

    session.add(board)
    session.flush()

    image = Image(
        board_id=board.board_id,
        uploaded_by_account_id=demo_account.account_id,
        storage_key=f"pytest/{uuid4()}.jpg",
        original_filename="test-image.jpg",
        mime_type="image/jpeg",
        file_size=123,
    )

    session.add(image)
    session.commit()
    session.refresh(image)

    return image


def test_analysis_request_lifecycle(db):
    """
    Проверяем нормальный жизненный цикл:

    created -> processing -> failed
    """
    session = db
    image = create_test_image(session)

    request = create_analysis_request_for_image(
        session,
        image.image_id,
    )

    assert request.analysis_request_id is not None
    assert request.image_id == image.image_id
    assert request.request_status == "created"
    assert request.created_at is not None

    request = start_processing(
        session,
        request.analysis_request_id,
    )

    assert request.request_status == "processing"
    assert request.started_at is not None

    request = fail_processing(
        session,
        request.analysis_request_id,
        error_code="TEST_ERROR",
        error_message="pytest lifecycle test",
    )

    assert request.request_status == "failed"
    assert request.finished_at is not None
    assert request.error_code == "TEST_ERROR"
    assert request.error_message == "pytest lifecycle test"


def test_repeated_analysis_creates_new_request(db):
    """
    Повторный запуск анализа одного изображения
    должен создавать новый AnalysisRequest,
    а не перезаписывать предыдущий.
    """
    session = db
    image = create_test_image(session)

    first = create_analysis_request_for_image(
        session,
        image.image_id,
    )

    second = create_analysis_request_for_image(
        session,
        image.image_id,
    )

    assert first.analysis_request_id is not None
    assert second.analysis_request_id is not None

    assert first.analysis_request_id != second.analysis_request_id

    assert first.image_id == image.image_id
    assert second.image_id == image.image_id

    # Первый запрос всё ещё должен существовать в БД.
    stored_first = session.get(
        AnalysisRequest,
        first.analysis_request_id,
    )

    assert stored_first is not None


def test_created_cannot_fail_directly(db):
    """
    Переход created -> failed запрещён.

    Сначала запрос должен перейти в processing.
    """
    session = db
    image = create_test_image(session)

    request = create_analysis_request_for_image(
        session,
        image.image_id,
    )

    assert request.request_status == "created"

    with pytest.raises(
        InvalidAnalysisRequestTransitionError
    ):
        fail_processing(
            session,
            request.analysis_request_id,
            error_code="INVALID_TRANSITION",
            error_message="created cannot go directly to failed",
        )


def test_processing_cannot_start_again(db):
    """
    Повторный переход processing -> processing запрещён.
    """
    session = db
    image = create_test_image(session)

    request = create_analysis_request_for_image(
        session,
        image.image_id,
    )

    request = start_processing(
        session,
        request.analysis_request_id,
    )

    assert request.request_status == "processing"

    with pytest.raises(
        InvalidAnalysisRequestTransitionError
    ):
        start_processing(
            session,
            request.analysis_request_id,
        )


def test_nonexistent_image_is_rejected(db):
    """
    Нельзя создать AnalysisRequest для изображения,
    которого нет в БД.
    """
    session = db

    with pytest.raises(ImageNotFoundError):
        create_analysis_request_for_image(
            session,
            999999999,
        )
def test_concurrent_processing_only_one_succeeds(db):
    """
    Два конкурентных запроса пытаются перевести
    один AnalysisRequest из created в processing.

    Ожидается:
    - один успешный переход;
    - один InvalidAnalysisRequestTransitionError;
    - итоговый статус processing.
    """
    image = create_test_image(db)

    request = create_analysis_request_for_image(
        db,
        image.image_id,
    )

    request_id = request.analysis_request_id

    barrier = Barrier(2)

    def worker():
        session = TestSessionLocal()

        try:
            barrier.wait(timeout=10)

            start_processing(
                session,
                request_id,
            )

            return "success"

        except InvalidAnalysisRequestTransitionError:
            return "conflict"

        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(worker)
            for _ in range(2)
        ]

        results = [
            future.result(timeout=20)
            for future in futures
        ]

    assert results.count("success") == 1
    assert results.count("conflict") == 1

    db.expire_all()

    stored_request = db.get(
        AnalysisRequest,
        request_id,
    )

    assert stored_request.request_status == "processing"