"""
Контрактные тесты OpenAPI для PCB AI Backend.

Проверяют маршруты, HTTP-методы и схемы запросов/ответов.
Не обращаются к PostgreSQL.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def openapi_schema():
    return app.openapi()


def get_schema(openapi, name):
    return openapi["components"]["schemas"][name]


def get_response_schema(openapi, path, method="get", status="200"):
    return openapi["paths"][path][method]["responses"][status][
        "content"
    ]["application/json"]["schema"]


EXPECTED_OPERATIONS = [
    ("get", "/health"),
    ("post", "/images"),
    ("get", "/images/{image_id}"),
    ("post", "/analysis-requests"),
    ("get", "/analysis-requests"),
    ("get", "/analysis-requests/{request_id}"),
]


@pytest.mark.parametrize("method,path", EXPECTED_OPERATIONS)
def test_required_operations_exist(openapi_schema, method, path):
    """Все обязательные операции присутствуют в OpenAPI."""
    assert path in openapi_schema["paths"]
    assert method in openapi_schema["paths"][path]


def test_openapi_endpoint_available():
    """Схема доступна через HTTP без запуска внешнего сервера."""
    with TestClient(app) as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")

    schema = response.json()
    assert schema["info"]["version"] == "0.1.0"
    assert "paths" in schema


def test_images_upload_uses_multipart(openapi_schema):
    """Загрузка изображения использует multipart/form-data."""
    operation = openapi_schema["paths"]["/images"]["post"]

    request_body = operation["requestBody"]

    assert request_body["required"] is True
    assert "multipart/form-data" in request_body["content"]

    schema = get_schema(
        openapi_schema,
        "Body_upload_image_images_post",
    )

    assert "file" in schema["required"]
    assert "file" in schema["properties"]


def test_image_upload_response_contract(openapi_schema):
    """Ответ загрузки содержит image_id."""
    schema = get_schema(openapi_schema, "ImageUploadResponse")

    assert "image_id" in schema["required"]
    assert "image_id" in schema["properties"]

    response_schema = get_response_schema(
        openapi_schema,
        "/images",
        method="post",
    )

    assert response_schema["$ref"].endswith("/ImageUploadResponse")


def test_analysis_create_request_contract(openapi_schema):
    """Запрос создания анализа требует image_id."""
    operation = openapi_schema["paths"]["/analysis-requests"]["post"]

    request_schema = operation["requestBody"]["content"][
        "application/json"
    ]["schema"]

    assert request_schema["$ref"].endswith("/AnalysisRequestCreate")

    schema = get_schema(openapi_schema, "AnalysisRequestCreate")

    assert "image_id" in schema["required"]


def test_analysis_create_response_contract(openapi_schema):
    """Создание анализа возвращает request_id и status."""
    schema = get_schema(
        openapi_schema,
        "AnalysisRequestCreateResponse",
    )

    assert {"request_id", "status"} <= set(schema["required"])

    response_schema = get_response_schema(
        openapi_schema,
        "/analysis-requests",
        method="post",
    )

    assert response_schema["$ref"].endswith(
        "/AnalysisRequestCreateResponse"
    )


def test_analysis_status_response_contract(openapi_schema):
    """Статус анализа содержит обязательные и дополнительные поля."""
    schema = get_schema(
        openapi_schema,
        "AnalysisRequestStatusResponse",
    )

    assert {"request_id", "status"} <= set(schema["required"])

    assert {
        "detections",
        "error_code",
        "error_message",
    } <= set(schema["properties"])

    response_schema = get_response_schema(
        openapi_schema,
        "/analysis-requests/{request_id}",
    )

    assert response_schema["$ref"].endswith(
        "/AnalysisRequestStatusResponse"
    )


def test_detection_response_contract(openapi_schema):
    """Дефект содержит тип, уверенность и координаты."""
    schema = get_schema(openapi_schema, "DetectionResponse")

    assert {
        "defect_type",
        "confidence",
        "bbox",
    } <= set(schema["required"])

    bbox_schema = get_schema(
        openapi_schema,
        "BoundingBoxResponse",
    )

    assert {
        "x_min",
        "y_min",
        "x_max",
        "y_max",
    } <= set(bbox_schema["required"])


def test_analysis_history_contract(openapi_schema):
    """История анализа возвращает массив записей."""
    response_schema = get_response_schema(
        openapi_schema,
        "/analysis-requests",
    )

    assert response_schema["type"] == "array"
    assert response_schema["items"]["$ref"].endswith(
        "/AnalysisHistoryItemResponse"
    )

    history_schema = get_schema(
        openapi_schema,
        "AnalysisHistoryItemResponse",
    )

    assert {
        "request_id",
        "image_id",
        "analysis_id",
        "status",
        "created_at",
        "finished_at",
        "detections_count",
    } <= set(history_schema["required"])


def test_validation_errors_documented(openapi_schema):
    """Для операций с параметрами задокументирована ошибка 422."""
    operations = [
        ("post", "/images"),
        ("get", "/images/{image_id}"),
        ("post", "/analysis-requests"),
        ("get", "/analysis-requests"),
        ("get", "/analysis-requests/{request_id}"),
    ]

    for method, path in operations:
        responses = openapi_schema["paths"][path][method]["responses"]
        assert "422" in responses, f"Missing 422: {method} {path}"
