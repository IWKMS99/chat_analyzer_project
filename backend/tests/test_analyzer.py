from pathlib import Path

from backend.app.services.analyzer import analyze_chat_file


FIXTURE = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "chat_small.json"


def test_analyze_chat_file_returns_contract():
    payload = analyze_chat_file(str(FIXTURE), "UTC")
    assert "summary" in payload
    assert "modules" in payload
    assert "metadata" in payload
    assert "activity" in payload["modules"]
