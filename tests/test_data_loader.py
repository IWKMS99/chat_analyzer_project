import json
from pathlib import Path

import pytest

from chat_analyzer.data_loader import (
    EmptyDataError,
    InvalidSchemaError,
    iter_chat_chunks,
    iter_chat_messages,
    load_and_process_chat_data,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_iter_chat_messages_streaming_records():
    records = list(iter_chat_messages(str(FIXTURES / "chat_small.json"), normalize=True))
    assert records
    assert all(r.sender for r in records)
    assert all(hasattr(r, "date") for r in records)


def test_iter_chat_chunks_schema_and_types():
    chunks = list(iter_chat_chunks(str(FIXTURES / "chat_small.json"), chunk_size=2))
    assert chunks
    df = chunks[0]
    assert {
        "from",
        "from_id",
        "message_id",
        "reply_to_message_id",
        "text_length",
        "is_forwarded",
        "is_edited",
        "is_deleted",
        "reactions",
    }.issubset(df.columns)
    assert str(df["text_length"].dtype) == "int32"


def test_load_and_process_chat_data_deprecated_wrapper():
    df = load_and_process_chat_data(str(FIXTURES / "chat_small.json"), chunk_size=2)
    assert not df.empty


def test_load_and_process_chat_data_empty_messages():
    with pytest.raises(EmptyDataError):
        load_and_process_chat_data(str(FIXTURES / "chat_empty_messages.json"))


def test_load_and_process_chat_data_invalid_schema():
    with pytest.raises(InvalidSchemaError):
        list(iter_chat_chunks(str(FIXTURES / "chat_invalid_schema.json")))


def test_deleted_message_without_author_is_kept(tmp_path: Path):
    payload = {
        "messages": [
            {
                "type": "message",
                "id": 1,
                "date": "2026-01-01T00:00:00",
                "media_type": "deleted_message",
                "text": "",
            }
        ]
    }
    path = tmp_path / "deleted.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    records = list(iter_chat_messages(str(path), normalize=True))
    assert len(records) == 1
    assert records[0].sender == "UnknownUser"
    assert records[0].is_deleted is True
