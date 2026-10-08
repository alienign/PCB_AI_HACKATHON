from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from ultralytics import YOLO

from app.core.config import settings


CLASS_NAMES = {
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


@dataclass(frozen=True)
class MLDetection:
    class_id: int
    defect_code: str
    confidence: float
    x_min: float
    y_min: float
    x_max: float
    y_max: float


class PCBDefectModel:
    def __init__(
        self,
        weights_path: str | Path,
        confidence_threshold: float = 0.25,
    ):
        self.weights_path = Path(weights_path)
        self.confidence_threshold = confidence_threshold

        if not self.weights_path.is_file():
            raise FileNotFoundError(
                f"ML weights not found: {self.weights_path}"
            )

        self.model = YOLO(str(self.weights_path))

    def predict(
        self,
        image_path: str | Path,
    ) -> list[MLDetection]:
        image_path = Path(image_path)

        if not image_path.is_file():
            raise FileNotFoundError(
                f"Image not found: {image_path}"
            )

        results = self.model.predict(
            source=str(image_path),
            conf=self.confidence_threshold,
            verbose=False,
        )

        if not results:
            return []

        result = results[0]
        image_height, image_width = result.orig_shape

        if image_width <= 0 or image_height <= 0:
            raise ValueError(
                "ML returned invalid image dimensions."
            )

        detections: list[MLDetection] = []

        for box in result.boxes:
            class_id = int(box.cls.item())

            if class_id not in CLASS_NAMES:
                raise ValueError(
                    f"Unknown ML class id: {class_id}"
                )

            confidence = float(box.conf.item())

            x1, y1, x2, y2 = (
                float(value)
                for value in box.xyxy[0].tolist()
            )

            x_min = max(0.0, min(1.0, x1 / image_width))
            y_min = max(0.0, min(1.0, y1 / image_height))
            x_max = max(0.0, min(1.0, x2 / image_width))
            y_max = max(0.0, min(1.0, y2 / image_height))

            if x_min >= x_max or y_min >= y_max:
                raise ValueError(
                    "ML returned invalid bounding box."
                )

            detections.append(
                MLDetection(
                    class_id=class_id,
                    defect_code=CLASS_NAMES[class_id],
                    confidence=confidence,
                    x_min=x_min,
                    y_min=y_min,
                    x_max=x_max,
                    y_max=y_max,
                )
            )

        return detections


@lru_cache(maxsize=1)
def get_ml_model() -> PCBDefectModel:
    return PCBDefectModel(
        weights_path=settings.ml_model_path,
    )


def analyze(
    image_path: str | Path,
) -> list[MLDetection]:
    return get_ml_model().predict(image_path)
