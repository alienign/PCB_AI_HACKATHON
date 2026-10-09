"""Tests for safe checkpoint downloading."""

import hashlib
import importlib.util
from io import BytesIO
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "fetch_model.py"
SPEC = importlib.util.spec_from_file_location("fetch_model_script", SCRIPT)
fetch_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fetch_module)


class FakeResponse(BytesIO):
    def geturl(self):
        return fetch_module.MODEL_URL


def test_successful_download(tmp_path, monkeypatch):
    content = b"trusted-checkpoint"
    expected_hash = hashlib.sha256(content).hexdigest()

    monkeypatch.setattr(fetch_module, "EXPECTED_SHA256", expected_hash)
    monkeypatch.setattr(
        fetch_module.urllib.request,
        "urlopen",
        lambda *args, **kwargs: FakeResponse(content),
    )

    destination = tmp_path / "models" / "best.pt"
    result = fetch_module.fetch_model(destination)

    assert result == destination
    assert destination.read_bytes() == content
    assert not list(destination.parent.glob("*.download"))


def test_invalid_hash_preserves_existing_model(tmp_path, monkeypatch):
    destination = tmp_path / "best.pt"
    destination.write_bytes(b"existing-model")

    monkeypatch.setattr(
        fetch_module.urllib.request,
        "urlopen",
        lambda *args, **kwargs: FakeResponse(b"invalid-model"),
    )

    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        fetch_module.fetch_model(destination)

    assert destination.read_bytes() == b"existing-model"
    assert not list(tmp_path.glob("*.download"))


def test_interrupted_download_preserves_existing_model(tmp_path, monkeypatch):
    destination = tmp_path / "best.pt"
    destination.write_bytes(b"existing-model")

    class InterruptedResponse(FakeResponse):
        def read(self, size=-1):
            raise ConnectionError("Connection interrupted")

    monkeypatch.setattr(
        fetch_module.urllib.request,
        "urlopen",
        lambda *args, **kwargs: InterruptedResponse(b"partial"),
    )

    with pytest.raises(ConnectionError, match="Connection interrupted"):
        fetch_module.fetch_model(destination)

    assert destination.read_bytes() == b"existing-model"
    assert not list(tmp_path.glob("*.download"))


def test_verified_model_skips_download(tmp_path, monkeypatch):
    content = b"trusted-checkpoint"
    destination = tmp_path / "best.pt"
    destination.write_bytes(content)

    monkeypatch.setattr(
        fetch_module,
        "EXPECTED_SHA256",
        hashlib.sha256(content).hexdigest(),
    )

    def forbidden_download(*args, **kwargs):
        raise AssertionError("Download must not be called")

    monkeypatch.setattr(
        fetch_module.urllib.request,
        "urlopen",
        forbidden_download,
    )

    assert fetch_module.fetch_model(destination) == destination
    assert destination.read_bytes() == content
