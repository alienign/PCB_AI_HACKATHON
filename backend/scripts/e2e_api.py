"""
PCB AI — полный HTTP E2E-тест.

Проверяет:
1. GET /health
2. POST /images
3. POST /analysis-requests
4. Ожидание завершения ML-анализа
5. Проверку результатов и координат дефектов
6. GET /analysis-requests — проверку истории

ВАЖНО:
Скрипт создаёт записи в PostgreSQL и сохраняет изображение.
Запускать исключительно на изолированном Backend с pcb_ai_test.
"""

import argparse
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import httpx


FINAL_STATUSES = {"completed", "failed"}


def check_response(response, expected_status=200):
    """Проверяет HTTP-статус и возвращает JSON."""
    if response.status_code != expected_status:
        raise RuntimeError(
            f"{response.request.method} {response.request.url}: "
            f"HTTP {response.status_code}, "
            f"ожидался {expected_status}. "
            f"Ответ: {response.text[:500]}"
        )

    return response.json()


def validate_detections(detections):
    """Проверяет структуру результатов ML."""
    if not isinstance(detections, list):
        raise RuntimeError("detections должен быть списком")

    for index, detection in enumerate(detections):
        if not isinstance(detection, dict):
            raise RuntimeError(
                f"Detection #{index}: ожидался объект"
            )

        defect_type = detection.get("defect_type")
        confidence = detection.get("confidence")
        bbox = detection.get("bbox")

        if not isinstance(defect_type, str) or not defect_type:
            raise RuntimeError(
                f"Detection #{index}: некорректный defect_type"
            )

        if (
            not isinstance(confidence, (int, float))
            or isinstance(confidence, bool)
            or not 0 <= confidence <= 1
        ):
            raise RuntimeError(
                f"Detection #{index}: некорректный confidence"
            )

        if not isinstance(bbox, dict):
            raise RuntimeError(
                f"Detection #{index}: отсутствует bbox"
            )

        required_coordinates = (
            "x_min",
            "y_min",
            "x_max",
            "y_max",
        )

        for coordinate in required_coordinates:
            value = bbox.get(coordinate)

            if (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not 0 <= value <= 1
            ):
                raise RuntimeError(
                    f"Detection #{index}: "
                    f"некорректная координата {coordinate}"
                )

        if (
            bbox["x_min"] >= bbox["x_max"]
            or bbox["y_min"] >= bbox["y_max"]
        ):
            raise RuntimeError(
                f"Detection #{index}: некорректные границы bbox"
            )


def main():
    parser = argparse.ArgumentParser(
        description="PCB AI — полный HTTP E2E-тест"
    )

    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8002",
        help="Адрес изолированного тестового Backend",
    )

    parser.add_argument(
        "--image",
        required=True,
        type=Path,
        help="Путь к тестовому PNG/JPEG",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=180,
        help="Максимальное время ожидания ML в секундах",
    )

    parser.add_argument(
        "--confirm-test-server",
        action="store_true",
        help="Подтверждение, что сервер использует pcb_ai_test",
    )

    args = parser.parse_args()

    if not args.confirm_test_server:
        parser.error(
            "Необходимо указать --confirm-test-server "
            "после проверки подключения сервера к pcb_ai_test."
        )

    parsed_url = urlparse(args.base_url)

    if (
        parsed_url.scheme != "http"
        or parsed_url.hostname not in ("127.0.0.1", "localhost")
        or parsed_url.port != 8002
        or parsed_url.username is not None
        or parsed_url.password is not None
        or parsed_url.path not in ("", "/")
        or parsed_url.query
        or parsed_url.fragment
    ):
        parser.error(
            "Разрешён только http://127.0.0.1:8002 "
            "или http://localhost:8002"
        )

    if args.timeout <= 0:
        parser.error("--timeout должен быть больше нуля")

    if not args.image.is_file():
        parser.error(
            f"Изображение не найдено: {args.image}"
        )

    if args.image.suffix.lower() not in (".png", ".jpg", ".jpeg"):
        parser.error("Поддерживаются только PNG и JPEG")

    base_url = args.base_url.rstrip("/")

    print("PCB AI — HTTP E2E")
    print("Сервер:", base_url)
    print("Изображение:", args.image)
    print("Ожидание ML:", args.timeout, "секунд")
    print()

    with httpx.Client(
        base_url=base_url,
        timeout=30.0,
        follow_redirects=False,
    ) as client:

        # 1. Проверка доступности API.
        print("[1/5] Проверяем /health")

        health = check_response(client.get("/health"))

        if health.get("status") != "ok":
            raise RuntimeError(
                f"Некорректный ответ /health: {health}"
            )

        print("OK: Backend доступен")

        # 2. Загрузка изображения.
        print("[2/5] Загружаем изображение")

        content_type = (
            "image/png"
            if args.image.suffix.lower() == ".png"
            else "image/jpeg"
        )

        with args.image.open("rb") as image_file:
            response = client.post(
                "/images",
                files={
                    "file": (
                        args.image.name,
                        image_file,
                        content_type,
                    )
                },
            )

        if response.status_code not in (200, 201):
            raise RuntimeError(
                f"Ошибка загрузки: HTTP {response.status_code}: "
                f"{response.text[:500]}"
            )

        image_data = response.json()
        image_id = image_data.get("image_id")

        if not isinstance(image_id, int) or isinstance(image_id, bool):
            raise RuntimeError(
                "API не вернул корректный image_id"
            )

        print("OK: image_id =", image_id)

        # 3. Создание запроса на анализ.
        print("[3/5] Создаём запрос на ML-анализ")

        response = client.post(
            "/analysis-requests",
            json={"image_id": image_id},
        )

        if response.status_code not in (200, 201, 202):
            raise RuntimeError(
                f"Ошибка создания анализа: "
                f"HTTP {response.status_code}: "
                f"{response.text[:500]}"
            )

        request_data = response.json()
        request_id = request_data.get("request_id")

        if (
            not isinstance(request_id, int)
            or isinstance(request_id, bool)
        ):
            raise RuntimeError(
                "API не вернул корректный request_id"
            )

        print("OK: request_id =", request_id)

        # 4. Ожидание завершения фонового анализа.
        print("[4/5] Ожидаем завершения YOLOv8")

        deadline = time.monotonic() + args.timeout
        result = None

        while time.monotonic() < deadline:
            result = check_response(
                client.get(f"/analysis-requests/{request_id}")
            )

            status = result.get("status")

            if status in FINAL_STATUSES:
                break

            if status not in ("created", "processing"):
                raise RuntimeError(
                    f"Неизвестный статус анализа: {status}"
                )

            print("Статус:", status)
            time.sleep(2)
        else:
            raise RuntimeError(
                f"ML-анализ не завершился за {args.timeout} секунд. "
                f"request_id={request_id}"
            )

        if result["status"] == "failed":
            raise RuntimeError(
                f"ML-анализ завершился ошибкой: "
                f"{result.get('error_code')}: "
                f"{result.get('error_message')}"
            )

        if result.get("request_id") != request_id:
            raise RuntimeError(
                "request_id в результате не совпадает"
            )

        detections = result.get("detections")
        validate_detections(detections)

        print("OK: ML-анализ завершён")
        print("Количество дефектов:", len(detections))

        # 5. Проверка истории анализов.
        print("[5/5] Проверяем историю анализов")

        history = check_response(
            client.get(
                "/analysis-requests",
                params={"limit": 100, "offset": 0},
            )
        )

        if not isinstance(history, list):
            raise RuntimeError(
                "История анализов должна быть списком"
            )

        matching_items = [
            item
            for item in history
            if item.get("request_id") == request_id
        ]

        if len(matching_items) != 1:
            raise RuntimeError(
                f"Запрос {request_id} не найден в истории "
                "или встречается несколько раз"
            )

        history_item = matching_items[0]

        if history_item.get("status") != "completed":
            raise RuntimeError(
                "В истории указан некорректный статус"
            )

        if history_item.get("image_id") != image_id:
            raise RuntimeError(
                "В истории указан другой image_id"
            )

        if history_item.get("detections_count") != len(detections):
            raise RuntimeError(
                "Количество дефектов в истории "
                "не совпадает с результатом анализа"
            )

        print("OK: анализ найден в истории")

    print()
    print("ПОЛНЫЙ HTTP E2E-ТЕСТ УСПЕШНО ПРОЙДЕН")
    print("image_id:", image_id)
    print("request_id:", request_id)
    print("detections:", len(detections))


if __name__ == "__main__":
    try:
        main()
    except (httpx.HTTPError, RuntimeError, ValueError) as exc:
        print(f"E2E FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
