"""
PCB AI Assistant — Backend Preflight Check.

Проверяет готовность Backend к запуску:
1. Настройки приложения.
2. Подключение к PostgreSQL.
3. Состояние миграций Alembic.
4. Наличие ML-модели.

Не изменяет базу данных.
"""

import sys
from pathlib import Path

from sqlalchemy import create_engine, text
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext


BACKEND_DIR = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings  # noqa: E402


def check_settings():
    print("\n[1/4] Проверка настроек")

    if not settings.database_url:
        print("FAIL: DATABASE_URL не настроен")
        return False

    print("OK: DATABASE_URL настроен")
    return True


def check_database():
    print("\n[2/4] Проверка PostgreSQL")

    engine = None

    try:
        engine = create_engine(
            settings.database_url,
            connect_args={"connect_timeout": 5},
        )

        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        print("OK: PostgreSQL доступен")
        return True

    except Exception as exc:
        print(f"FAIL: PostgreSQL недоступен: {exc}")
        return False

    finally:
        if engine is not None:
            engine.dispose()


def check_migrations():
    print("\n[3/4] Проверка миграций Alembic")

    engine = None

    try:
        config = Config(str(BACKEND_DIR / "alembic.ini"))
        script = ScriptDirectory.from_config(config)

        expected_heads = set(script.get_heads())

        engine = create_engine(
            settings.database_url,
            connect_args={"connect_timeout": 5},
        )

        with engine.connect() as connection:
            context = MigrationContext.configure(connection)
            current_heads = set(context.get_current_heads())

        if current_heads != expected_heads:
            print(
                "FAIL: Миграции неактуальны. "
                f"База: {sorted(current_heads)}, "
                f"Код: {sorted(expected_heads)}"
            )
            return False

        print("OK: Миграции актуальны")
        return True

    except Exception as exc:
        print(f"FAIL: Ошибка проверки миграций: {exc}")
        return False

    finally:
        if engine is not None:
            engine.dispose()


def check_model():
    print("\n[4/4] Проверка ML-модели")

    model_path = Path(settings.ml_model_path)

    if not model_path.is_absolute():
        model_path = BACKEND_DIR / model_path

    if not model_path.is_file():
        print(f"FAIL: ML-модель не найдена: {model_path}")
        return False

    if model_path.stat().st_size == 0:
        print(f"FAIL: ML-модель пуста: {model_path}")
        return False

    print(f"OK: ML-модель найдена: {model_path}")
    return True


def main():
    print("=" * 50)
    print("PCB AI Assistant — Backend Preflight")
    print("=" * 50)

    results = []

    settings_ok = check_settings()
    results.append(settings_ok)

    if settings_ok:
        results.append(check_database())
        results.append(check_migrations())
    else:
        print("\n[2/4] SKIP: Нет DATABASE_URL")
        print("[3/4] SKIP: Нет DATABASE_URL")
        results.extend([False, False])

    results.append(check_model())

    print("\n" + "=" * 50)

    if all(results):
        print("PREFLIGHT PASSED: Backend готов к запуску")
        return 0

    print("PREFLIGHT FAILED: Есть проблемы")
    return 1


if __name__ == "__main__":
    sys.exit(main())