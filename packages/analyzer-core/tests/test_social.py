from pathlib import Path

from chat_analyzer_core.aggregators import SocialAggregator
from chat_analyzer_core.data_loader import iter_chat_chunks
from chat_analyzer_api.workers.analyzer_flow import localize_chunk


FIXTURES = Path(__file__).parent / "fixtures"


def test_social_aggregator_has_edited_columns():
    agg = SocialAggregator()
    for chunk in iter_chat_chunks(str(FIXTURES / "chat_small.json"), chunk_size=3):
        chunk = localize_chunk(chunk, "UTC")
        agg.update(chunk)
    out = agg.result()
    assert "reactions_received" in out
    assert "edited" in out
    assert {"edited_ratio", "edited", "total"}.issubset(out["edited"].columns)
    assert "deleted_ratio" not in out["edited"].columns
