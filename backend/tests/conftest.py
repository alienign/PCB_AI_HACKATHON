import os

import pytest
from sqlalchemy import text


@pytest.fixture
def safe_test_db():
    """Сессия только для изолированной тестовой PostgreSQL-базы."""
    database_url = os.getenv("DATABASE_URL", "")
    test_database_url = os.getenv("TEST_DATABASE_URL", "")

    if not database_url or database_url != test_database_url:
        pytest.fail(
            "DATABASE_URL and TEST_DATABASE_URL must be set and match"
        )

    # Импортируем после проверки переменных окружения.
    from app.db.session import SessionLocal

    with SessionLocal() as session:
        actual_database = session.execute(
            text("SELECT current_database()")
        ).scalar_one()

        if actual_database != "pcb_ai_test":
            pytest.fail(
                f"Expected pcb_ai_test, got {actual_database}"
            )

        try:
            yield session
        finally:
            session.rollback()
