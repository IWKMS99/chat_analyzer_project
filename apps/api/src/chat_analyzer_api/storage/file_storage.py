from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from chat_analyzer_api.storage.base import StorageBackend


class FileStorage(StorageBackend):
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def write_bytes(self, path: str, payload: bytes) -> None:
        resolved = self._resolve(path)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_bytes(payload)

    def write_json(self, path: str, payload: dict[str, Any]) -> None:
        content = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.write_bytes(path, content)

    def copy_file(self, path: str, source_file_path: str) -> None:
        resolved = self._resolve(path)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_file_path, resolved)

    def read_bytes(self, path: str) -> bytes:
        return self._resolve(path).read_bytes()

    def read_json(self, path: str) -> dict[str, Any]:
        parsed = json.loads(self.read_bytes(path).decode("utf-8"))
        if not isinstance(parsed, dict):
            raise ValueError("JSON payload must be an object")
        return parsed

    def download_to_file(self, path: str, file_path: str) -> None:
        source = self._resolve(path)
        target = Path(file_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)

    def remove_path(self, path: str | None) -> None:
        if not path:
            return
        resolved = self._resolve(path)
        if resolved.exists() and resolved.is_file():
            resolved.unlink()

    def exists(self, path: str) -> bool:
        return self._resolve(path).exists()

    def healthcheck(self) -> bool:
        try:
            self.base_dir.mkdir(parents=True, exist_ok=True)
            probe = self.base_dir / ".healthcheck"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return True
        except OSError:
            return False

    def _resolve(self, relative_path: str) -> Path:
        candidate = Path(relative_path)
        if candidate.is_absolute():
            raise ValueError("Storage paths must be relative")
        resolved = (self.base_dir / candidate).resolve()
        if not resolved.is_relative_to(self.base_dir):
            raise ValueError("Storage path escapes base directory")
        return resolved
