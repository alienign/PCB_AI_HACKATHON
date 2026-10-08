from dataclasses import dataclass


@dataclass
class MLDetection:
    defect_type: str
    confidence: float
    x_min: float
    y_min: float
    x_max: float
    y_max: float


def detect_defects(image_path: str) -> list[MLDetection]:
    """Temporary stub. Real YOLO inference is not connected yet."""
    raise NotImplementedError(
        "YOLO inference is not connected yet."
    )