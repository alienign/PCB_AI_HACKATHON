import asyncio
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers

from app.services.image_storage import ImageStorage


def test_partial_file_is_removed_on_write_error(tmp_path):
    """При ошибке записи частично созданный файл должен удаляться."""

    storage = ImageStorage(storage_path=str(tmp_path))

    file = UploadFile(
        filename="board.png",
        file=None,
        headers=Headers({"content-type": "image/png"}),
    )

    async def fake_seek(offset):
        return None

    async def fake_read():
        return b"image content"

    file.seek = fake_seek
    file.read = fake_read

    original_write_bytes = Path.write_bytes

    def broken_write_bytes(path, data):
        # Имитируем частичную запись изображения.
        original_write_bytes(path, data[:5])

        # После записи нескольких байтов возникает ошибка.
        raise OSError("Simulated disk write failure")

    with patch.object(
        Path,
        "write_bytes",
        broken_write_bytes,
    ):
        with pytest.raises(
            OSError,
            match="Simulated disk write failure",
        ):
            asyncio.run(storage.save(file))

    # После ошибки временная папка должна быть пустой.
    assert list(tmp_path.iterdir()) == []
