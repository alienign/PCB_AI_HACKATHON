from pathlib import Path

import pytest

from app.services.ml_service import CLASS_NAMES, PCBDefectModel


EXPECTED_CLASS_NAMES = {
    0: "short",
    1: "spur",
    2: "spurious_copper",
    3: "open",
    4: "mouse_bite",
    5: "hole_breakout",
    6: "conductor_scratch",
    7: "conductor_foreign_object",
    8: "base_material_foreign_object",
}


def test_class_mapping_is_correct():
    assert CLASS_NAMES == EXPECTED_CLASS_NAMES
    assert len(CLASS_NAMES) == 9


def test_missing_weights_are_rejected():
    missing_path = Path(
        "/tmp/pcb-ai-model-that-does-not-exist.pt"
    )

    with pytest.raises(FileNotFoundError):
        PCBDefectModel(missing_path)


def test_missing_image_is_rejected(tmp_path):
    model = PCBDefectModel.__new__(PCBDefectModel)

    missing_image = tmp_path / "missing.jpg"

    with pytest.raises(FileNotFoundError):
        model.predict(missing_image)



def test_valid_checkpoint_is_loaded(tmp_path, monkeypatch):
    from unittest.mock import Mock
    from app.services import ml_service

    weights = tmp_path / "best.pt"
    weights.write_bytes(b"trusted-test-checkpoint")

    expected_hash = ml_service.calculate_sha256(weights)

    monkeypatch.setattr(
        ml_service,
        "TRUSTED_MODEL_SHA256",
        expected_hash,
    )

    fake_yolo = Mock()
    monkeypatch.setattr(ml_service, "YOLO", fake_yolo)

    model = PCBDefectModel(weights)

    fake_yolo.assert_called_once_with(str(weights))
    assert model.model is fake_yolo.return_value


def test_invalid_checkpoint_is_rejected_before_yolo(tmp_path, monkeypatch):
    from unittest.mock import Mock
    from app.services import ml_service

    weights = tmp_path / "best.pt"
    weights.write_bytes(b"untrusted-checkpoint")

    fake_yolo = Mock()
    monkeypatch.setattr(ml_service, "YOLO", fake_yolo)

    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        PCBDefectModel(weights)

    fake_yolo.assert_not_called()
