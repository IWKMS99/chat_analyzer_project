import pandas as pd

from chat_analyzer_core.aggregators import DialogAggregator


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
