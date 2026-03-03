from pathlib import Path

from chat_analyzer_core.data_loader import iter_chat_chunks
from chat_analyzer_api.workers.analyzer_flow import localize_chunk


FIXTURES = Path(__file__).parent / "fixtures"


def test_timezone_conversion_changes_hour_to_local():
    first_chunk = next(iter_chat_chunks(str(FIXTURES / "chat_small.json"), chunk_size=5))
    utc_hour = int(first_chunk.iloc[0]["date"].hour)
    localized = localize_chunk(first_chunk, "Europe/Moscow")
    moscow_hour = int(localized.iloc[0]["hour"])
    assert moscow_hour == (utc_hour + 3) % 24


def test_invalid_timezone_falls_back_to_utc():
    first_chunk = next(iter_chat_chunks(str(FIXTURES / "chat_small.json"), chunk_size=5))
    localized = localize_chunk(first_chunk, "RU/Moscow")
    assert str(localized.iloc[0]["date"].tz) == "UTC"
