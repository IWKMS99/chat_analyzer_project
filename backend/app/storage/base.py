from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class StorageBackend(ABC):
    @abstractmethod
    def write_bytes(self, path: str, payload: bytes) -> None:
        raise NotImplementedError

    @abstractmethod
    def write_json(self, path: str, payload: dict[str, Any]) -> None:
        raise NotImplementedError

    @abstractmethod
    def copy_file(self, path: str, source_file_path: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def read_bytes(self, path: str) -> bytes:
        raise NotImplementedError

    @abstractmethod
    def read_json(self, path: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def download_to_file(self, path: str, file_path: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def remove_path(self, path: str | None) -> None:
        raise NotImplementedError

    @abstractmethod
    def exists(self, path: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def healthcheck(self) -> bool:
        raise NotImplementedError
