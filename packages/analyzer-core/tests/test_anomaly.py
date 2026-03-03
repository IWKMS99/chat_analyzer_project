from pathlib import Path

from chat_analyzer_core.aggregators import AnomalyAggregator
from chat_analyzer_core.data_loader import iter_chat_chunks
from chat_analyzer_api.workers.analyzer_flow import localize_chunk


FIXTURES = Path(__file__).parent / "fixtures"


def test_anomaly_streaming_has_non_empty_anomaly_frame():
    agg = AnomalyAggregator(threshold=0.5, mode="robust")
    for chunk in iter_chat_chunks(str(FIXTURES / "chat_small.json"), chunk_size=2):
        chunk = localize_chunk(chunk, "UTC")
        agg.update(chunk)
    out = agg.result()
    assert "daily" in out
    assert not out["daily"].empty


def test_anomaly_modes_return_metrics_streaming():
    agg = AnomalyAggregator(threshold=0.5, mode="both")
    for chunk in iter_chat_chunks(str(FIXTURES / "chat_small.json"), chunk_size=2):
        chunk = localize_chunk(chunk, "UTC")
        agg.update(chunk)
    out = agg.result()
    assert "metrics" in out
    assert out["metrics"]["mode"] == "both"
