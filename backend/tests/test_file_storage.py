from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.app.storage.file_storage import FileStorage


def test_file_storage_write_read_json(tmp_path: Path):
    storage = FileStorage(str(tmp_path / "data"))
    payload = {"ok": True, "value": 1}

    storage.write_json("results/a1.json", payload)
    loaded = storage.read_json("results/a1.json")

    assert loaded == payload


def test_file_storage_copy_and_download(tmp_path: Path):
    storage = FileStorage(str(tmp_path / "data"))
    source = tmp_path / "upload.json"
    source.write_text('{"messages": []}', encoding="utf-8")

    storage.copy_file("uploads/a1.json", str(source))

    target = tmp_path / "downloaded.json"
    storage.download_to_file("uploads/a1.json", str(target))

    assert target.read_text(encoding="utf-8") == '{"messages": []}'


def test_file_storage_remove_and_exists(tmp_path: Path):
    storage = FileStorage(str(tmp_path / "data"))
    storage.write_bytes("results/a1.json", b"{}")
    assert storage.exists("results/a1.json") is True

    storage.remove_path("results/a1.json")
    assert storage.exists("results/a1.json") is False


def test_file_storage_blocks_path_escape(tmp_path: Path):
    storage = FileStorage(str(tmp_path / "data"))
    with pytest.raises(ValueError):
        storage.write_json("../evil.json", {"x": 1})


def test_file_storage_healthcheck(tmp_path: Path):
    storage = FileStorage(str(tmp_path / "data"))
    assert storage.healthcheck() is True
