import pandas as pd

from chat_analyzer_api.core.serializers import dataframe_to_records


def test_dataframe_to_records_includes_datetime_iso():
    df = pd.DataFrame([{"ts": pd.Timestamp("2026-01-01T00:00:00Z"), "value": 1}])
    records = dataframe_to_records(df)
    assert records[0]["ts"].startswith("2026-01-01T00:00:00")


def test_dataframe_to_records_with_index():
    df = pd.DataFrame({"count": [1, 2]}, index=["a", "b"])
    records = dataframe_to_records(df, include_index=True, index_name="key")
    assert records[0]["key"] == "a"


def test_dataframe_to_records_does_not_include_index_when_disabled():
    df = pd.DataFrame({"value": [1, 2]}, index=["x", "y"])
    records = dataframe_to_records(df, include_index=False)
    assert "index" not in records[0]
    assert "x" not in records[0].values()
