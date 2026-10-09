from fastapi import APIRouter
from fastapi.testclient import TestClient

from app.main import app


def test_unexpected_error_returns_json():
    """
    Неожиданная ошибка Backend должна возвращать
    HTTP 500 с безопасным JSON.
    """

    # Создаём отдельный тестовый маршрут.
    # PostgreSQL и реальные изображения не используются.
    router = APIRouter()

    @router.get("/test-internal-error")
    def broken_endpoint():
        raise RuntimeError("Simulated internal failure")

    # Подключаем тестовый маршрут только на время проверки.
    app.include_router(router)

    try:
        with TestClient(
            app,
            raise_server_exceptions=False,
        ) as client:
            response = client.get("/test-internal-error")

        assert response.status_code == 500

        assert response.json() == {
            "detail": "Internal server error."
        }

    finally:
        # Убираем тестовый маршрут из приложения.
        app.router.routes = [
            route
            for route in app.router.routes
            if getattr(route, "path", None)
            != "/test-internal-error"
        ]
