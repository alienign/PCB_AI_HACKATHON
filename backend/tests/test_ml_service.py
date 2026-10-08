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
