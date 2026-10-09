"""
PCB AI — HTTP API smoke-test.

Проверяет:
1. GET /health
2. POST /images
3. POST /analysis-requests
4. GET /analysis-requests/{request_id}

Создаёт записи на сервере. Запускать только
на отдельном тестовом Backend с тестовой БД.
"""

import argparse
import sys
from pathlib import Path
from urllib.parse import urlparse

import httpx


def check_response(response, expected_status=200):
    """Проверяет HTTP-статус и выводит ошибку при сбое."""
    if response.status_code != expected_status:
        raise RuntimeError(
            f"{response.request.method} {response.request.url}: "
            f"HTTP {response.status_code}, "
            f"ожидался {expected_status}. "
            f"Ответ: {response.text[:500]}"
        )
    return response.json()


def main():
    parser = argparse.ArgumentParser(
        description="PCB AI Backend API smoke-test"
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Адрес тестового Backend",
    )
    parser.add_argument(
        "--image",
        required=True,
        type=Path,
        help="Путь к тестовому PNG/JPEG",
    )
    parser.add_argument(
        "--confirm-test-server",
        action="store_true",
        help="Подтверждение, что сервер использует тестовую БД",
    )

    args = parser.parse_args()

    if not args.confirm_test_server:
        parser.error(
            "Укажи --confirm-test-server только после "
            "проверки конфигурации тестового Backend."
        )

    parsed_url = urlparse(args.base_url)

    if parsed_url.hostname not in ("127.0.0.1", "localhost"):
        parser.error(
            "Разрешён только локальный тестовый сервер."
        )

    if not args.image.is_file():
        parser.error(f"Файл изображения не найден: {args.image}")

    if args.image.suffix.lower() not in (".png", ".jpg", ".jpeg"):
        parser.error("Поддерживаются только PNG и JPEG")

    base_url = args.base_url.rstrip("/")

    print("PCB AI API smoke-test")
    print("Сервер:", base_url)
    print("Изображение:", args.image)
    print()

    with httpx.Client(
        base_url=base_url,
        timeout=30.0,
        follow_redirects=False,
    ) as client:

        print("[1/4] Проверяем /health")

        response = client.get("/health")
        check_response(response)

        print("OK: Backend доступен")

        print("[2/4] Загружаем изображение")

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

        # До согласования контракта допускаем оба успешных статуса.
        if response.status_code not in (200, 201):
            raise RuntimeError(
                f"Ошибка загрузки: HTTP {response.status_code}: "
                f"{response.text[:500]}"
            )

        image_data = response.json()
        image_id = image_data.get("image_id")

        if not image_id:
            raise RuntimeError("В ответе отсутствует image_id")

        print("OK: image_id =", image_id)

        print("[3/4] Создаём запрос на анализ")

        response = client.post(
            "/analysis-requests",
            json={"image_id": image_id},
        )

        if response.status_code not in (200, 201, 202):
            raise RuntimeError(
                f"Ошибка создания анализа: HTTP {response.status_code}: "
                f"{response.text[:500]}"
            )

        analysis_data = response.json()
        request_id = analysis_data.get("request_id")

        if not request_id:
            raise RuntimeError("В ответе отсутствует request_id")

        print("OK: request_id =", request_id)

        print("[4/4] Получаем статус анализа")

        response = client.get(
            f"/analysis-requests/{request_id}"
        )

        status_data = check_response(response)

        if "status" not in status_data:
            raise RuntimeError("В ответе отсутствует status")

        print("OK: status =", status_data["status"])

    print()
    print("API SMOKE-TEST УСПЕШНО ПРОЙДЕН")
    print(
        "Примечание: проверено получение статуса, "
        "а не завершение ML-анализа."
    )


if __name__ == "__main__":
    try:
        main()
    except (httpx.HTTPError, RuntimeError, ValueError) as exc:
        print(f"SMOKE-TEST FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
