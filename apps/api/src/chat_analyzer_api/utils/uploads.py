from __future__ import annotations

import os
import tempfile
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import HTTPException, UploadFile, status


@asynccontextmanager
async def managed_upload_temp_file(upload_file: UploadFile, max_size_bytes: int) -> AsyncIterator[tuple[str, int]]:
    temp_upload_path = None
    try:
        temp_upload_path, size = await persist_upload_to_temp(upload_file, max_size_bytes)
        yield temp_upload_path, size
    finally:
        if temp_upload_path:
            cleanup_temp_file(temp_upload_path)


async def persist_upload_to_temp(upload_file: UploadFile, max_size_bytes: int) -> tuple[str, int]:
    current_size = 0
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
        file_path = tmp.name
        while True:
            chunk = await upload_file.read(1024 * 1024)
            if not chunk:
                break
            current_size += len(chunk)
            if current_size > max_size_bytes:
                cleanup_temp_file(file_path)
                raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="File exceeds upload limit")
            tmp.write(chunk)

    if current_size == 0:
        cleanup_temp_file(file_path)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")

    return file_path, current_size


def cleanup_temp_file(path: str) -> None:
    if path and os.path.exists(path):
        os.remove(path)
