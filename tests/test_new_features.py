from pathlib import Path

from chat_analyzer.analysis.aggregators import AnomalyAggregator, SocialAggregator
from chat_analyzer.data_loader import iter_chat_chunks

FIXTURES = Path(__file__).parent / "fixtures"


def test_anomaly_modes_return_metrics_streaming():
    ag = AnomalyAggregator(threshold=0.5, mode="both")
    for chunk in iter_chat_chunks(str(FIXTURES / "chat_small.json"), chunk_size=2):
        ag.update(chunk)
    result = ag.result()
    assert "metrics" in result
    assert result["metrics"]["mode"] == "both"


def test_social_aggregator_has_edited_deleted_columns():
    sg = SocialAggregator()
    for chunk in iter_chat_chunks(str(FIXTURES / "chat_small.json"), chunk_size=3):
        sg.update(chunk)
    data = sg.result()
    assert "edited_deleted" in data
    assert {"edited_ratio", "deleted_ratio"}.issubset(data["edited_deleted"].columns)
