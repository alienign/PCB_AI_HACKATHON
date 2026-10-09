"""Download and verify the trusted PCB YOLO checkpoint."""

import argparse
import hashlib
import os
import ssl
import tempfile

import certifi
import urllib.request
from pathlib import Path

MODEL_URL = (
    "https://huggingface.co/Janani-V/"
    "pcb-defect-yolov8m-dspcbsd/resolve/main/best.pt"
)
EXPECTED_SHA256 = (
    "e0978435538c462009835c810787e32030154c40918b7211a0b3f409ec36453c"
)
DEFAULT_DESTINATION = Path(__file__).resolve().parents[1] / "models" / "best.pt"


def calculate_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch_model(destination: Path = DEFAULT_DESTINATION) -> Path:
    destination = Path(destination).expanduser()
    destination.parent.mkdir(parents=True, exist_ok=True)

    if destination.is_file():
        if calculate_sha256(destination) == EXPECTED_SHA256:
            print(f"Verified model already exists: {destination}")
            return destination

    temporary_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=".best-",
            suffix=".download",
            dir=destination.parent,
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            digest = hashlib.sha256()

            with urllib.request.urlopen(MODEL_URL, timeout=60, context=ssl.create_default_context(cafile=certifi.where())) as response:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break

                    temporary.write(chunk)
                    digest.update(chunk)

            temporary.flush()
            os.fsync(temporary.fileno())

        actual_sha256 = digest.hexdigest()

        if actual_sha256 != EXPECTED_SHA256:
            raise ValueError(
                "SHA-256 mismatch: refusing to install checkpoint. "
                f"Expected {EXPECTED_SHA256}, got {actual_sha256}"
            )

        os.replace(temporary_path, destination)
        temporary_path = None

        print(f"Verified model installed: {destination}")
        print(f"SHA-256: {actual_sha256}")
        return destination

    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download and verify the trusted PCB model."
    )
    parser.add_argument(
        "--destination",
        type=Path,
        default=DEFAULT_DESTINATION,
    )
    args = parser.parse_args()
    fetch_model(args.destination)


if __name__ == "__main__":
    main()
