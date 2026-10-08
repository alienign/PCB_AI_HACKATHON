from pathlib import Path
from unittest.mock import MagicMock

import pytest

from scripts import preflight


def test_settings_success(monkeypatch):
    """DATABASE_URL задан."""
    monkeypatch.setattr(
        preflight.settings,
        "database_url",
        "postgresql://localhost/test",
    )

    assert preflight.check_settings() is True


def test_settings_missing(monkeypatch):
    """DATABASE_URL отсутствует."""
    monkeypatch.setattr(
        preflight.settings,
        "database_url",
        "",
    )

    assert preflight.check_settings() is False


def test_database_success(monkeypatch):
    """PostgreSQL отвечает на SELECT 1."""
    engine = MagicMock()

    monkeypatch.setattr(
        preflight,
        "create_engine",
        lambda *args, **kwargs: engine,
    )

    assert preflight.check_database() is True
    engine.connect.return_value.__enter__.return_value.execute.assert_called_once()
    engine.dispose.assert_called_once()


def test_database_failure(monkeypatch):
    """Ошибка подключения корректно обрабатывается."""

    def fake_create_engine(*args, **kwargs):
        raise ConnectionError("Database unavailable")

    monkeypatch.setattr(
        preflight,
        "create_engine",
        fake_create_engine,
    )

    assert preflight.check_database() is False


def test_migrations_success(monkeypatch):
    """Версии миграций совпадают."""
    engine = MagicMock()
    script = MagicMock()
    script.get_heads.return_value = ["revision_123"]

    context = MagicMock()
    context.get_current_heads.return_value = ["revision_123"]

    monkeypatch.setattr(
        preflight,
        "create_engine",
        lambda *args, **kwargs: engine,
    )
    monkeypatch.setattr(
        preflight.ScriptDirectory,
        "from_config",
        lambda *args, **kwargs: script,
    )
    monkeypatch.setattr(
        preflight.MigrationContext,
        "configure",
        lambda *args, **kwargs: context,
    )

    assert preflight.check_migrations() is True
    engine.dispose.assert_called_once()


def test_migrations_outdated(monkeypatch):
    """Неактуальные миграции обнаруживаются."""
    engine = MagicMock()
    script = MagicMock()
    script.get_heads.return_value = ["revision_new"]

    context = MagicMock()
    context.get_current_heads.return_value = ["revision_old"]

    monkeypatch.setattr(
        preflight,
        "create_engine",
        lambda *args, **kwargs: engine,
    )
    monkeypatch.setattr(
        preflight.ScriptDirectory,
        "from_config",
        lambda *args, **kwargs: script,
    )
    monkeypatch.setattr(
        preflight.MigrationContext,
        "configure",
        lambda *args, **kwargs: context,
    )

    assert preflight.check_migrations() is False


def test_model_success(monkeypatch, tmp_path):
    """Файл модели существует и не пуст."""
    model = tmp_path / "best.pt"
    model.write_bytes(b"fake-model-content")

    monkeypatch.setattr(
        preflight.settings,
        "ml_model_path",
        str(model),
    )

    assert preflight.check_model() is True


def test_model_missing(monkeypatch, tmp_path):
    """Отсутствующая модель обнаруживается."""
    model = tmp_path / "missing.pt"

    monkeypatch.setattr(
        preflight.settings,
        "ml_model_path",
        str(model),
    )

    assert preflight.check_model() is False


def test_model_empty(monkeypatch, tmp_path):
    """Пустая модель обнаруживается."""
    model = tmp_path / "empty.pt"
    model.touch()

    monkeypatch.setattr(
        preflight.settings,
        "ml_model_path",
        str(model),
    )

    assert preflight.check_model() is False


def test_main_success(monkeypatch):
    """Успешные проверки дают код завершения 0."""
    monkeypatch.setattr(preflight, "check_settings", lambda: True)
    monkeypatch.setattr(preflight, "check_database", lambda: True)
    monkeypatch.setattr(preflight, "check_migrations", lambda: True)
    monkeypatch.setattr(preflight, "check_model", lambda: True)

    assert preflight.main() == 0


def test_main_failure(monkeypatch):
    """Ошибка любой проверки даёт код завершения 1."""
    monkeypatch.setattr(preflight, "check_settings", lambda: True)
    monkeypatch.setattr(preflight, "check_database", lambda: False)
    monkeypatch.setattr(preflight, "check_migrations", lambda: True)
    monkeypatch.setattr(preflight, "check_model", lambda: True)

    assert preflight.main() == 1


def test_main_skips_database_without_settings(monkeypatch):
    """Без DATABASE_URL подключения к базе не выполняются."""
    monkeypatch.setattr(preflight, "check_settings", lambda: False)
    monkeypatch.setattr(preflight, "check_model", lambda: True)

    def unexpected_database_call():
        pytest.fail("Database check must not run")

    monkeypatch.setattr(
        preflight,
        "check_database",
        unexpected_database_call,
    )
    monkeypatch.setattr(
        preflight,
        "check_migrations",
        unexpected_database_call,
    )

    assert preflight.main() == 1