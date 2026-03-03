from pathlib import Path

import pandas as pd

from chat_analyzer.analysis.aggregators import AnomalyAggregator, DialogAggregator, SocialAggregator
from chat_analyzer.data_loader import iter_chat_chunks
from backend.app.services.analyzer import localize_chunk

FIXTURES = Path(__file__).parent / "fixtures"


def test_anomaly_modes_return_metrics_streaming():
    ag = AnomalyAggregator(threshold=0.5, mode="both")
    for chunk in iter_chat_chunks(str(FIXTURES / "chat_small.json"), chunk_size=2):
        chunk = localize_chunk(chunk, "UTC")
        ag.update(chunk)
    result = ag.result()
    assert "metrics" in result
    assert result["metrics"]["mode"] == "both"


def test_social_aggregator_has_edited_deleted_columns():
    sg = SocialAggregator()
    for chunk in iter_chat_chunks(str(FIXTURES / "chat_small.json"), chunk_size=3):
        chunk = localize_chunk(chunk, "UTC")
        sg.update(chunk)
    data = sg.result()
    assert "edited_deleted" in data
    assert {"edited_ratio", "deleted_ratio"}.issubset(data["edited_deleted"].columns)


def test_dialog_aggregator_prefers_reply_to_message_id():
    agg = DialogAggregator(response_limit_minutes=60, session_gap_minutes=30)
    chunk = pd.DataFrame(
        [
            {"from": "Alice", "date": pd.Timestamp("2026-01-01T10:00:00Z"), "hour": 10, "message_id": 1, "reply_to_message_id": None},
            {"from": "Bob", "date": pd.Timestamp("2026-01-01T10:01:00Z"), "hour": 10, "message_id": 2, "reply_to_message_id": None},
            {"from": "Carol", "date": pd.Timestamp("2026-01-01T10:02:00Z"), "hour": 10, "message_id": 3, "reply_to_message_id": 1},
        ]
    )
    agg.update(chunk)
    out = agg.result()
    edges = out["reply_edges"]
    assert not edges.empty
    matched = edges[(edges["from"] == "Carol") & (edges["prev_from"] == "Alice")]
    assert not matched.empty
