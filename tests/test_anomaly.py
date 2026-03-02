from pathlib import Path

from chat_analyzer.analysis.aggregators import AnomalyAggregator
from chat_analyzer.data_loader import iter_chat_chunks


FIXTURES = Path(__file__).parent / "fixtures"


def test_anomaly_streaming_has_non_empty_anomaly_frame():
    agg = AnomalyAggregator(threshold=0.5, mode="robust")
    for chunk in iter_chat_chunks(str(FIXTURES / "chat_small.json"), chunk_size=2):
        agg.update(chunk)
    out = agg.result()
    assert "daily" in out
    assert not out["daily"].empty
