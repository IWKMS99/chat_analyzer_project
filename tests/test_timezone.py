from pathlib import Path

from chat_analyzer.data_loader import iter_chat_chunks


FIXTURES = Path(__file__).parent / "fixtures"


def test_timezone_conversion_changes_hour_to_local():
    first_chunk = next(iter_chat_chunks(str(FIXTURES / "chat_small.json"), chunk_size=5))
    utc_hour = int(first_chunk.iloc[0]["hour"])
    moscow_hour = int(first_chunk.iloc[0]["date"].tz_convert("Europe/Moscow").hour)
    assert moscow_hour == (utc_hour + 3) % 24
