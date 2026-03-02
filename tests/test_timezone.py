from pathlib import Path

from chat_analyzer.data_loader import iter_chat_chunks
from main import _localize_chunk


FIXTURES = Path(__file__).parent / "fixtures"


def test_timezone_conversion_changes_hour_to_local():
    first_chunk = next(iter_chat_chunks(str(FIXTURES / "chat_small.json"), chunk_size=5))
    utc_hour = int(first_chunk.iloc[0]["date"].hour)
    localized = _localize_chunk(first_chunk, "Europe/Moscow")
    moscow_hour = int(localized.iloc[0]["hour"])
    assert moscow_hour == (utc_hour + 3) % 24
