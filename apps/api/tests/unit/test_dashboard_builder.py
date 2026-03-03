from __future__ import annotations

from chat_analyzer_api.services.dashboard_builder import build_dashboard_payload


def test_dashboard_builder_returns_declarative_contract():
    result = {
        "summary": {
            "total_messages": 10,
            "participants": 2,
            "start": "2026-01-01T00:00:00+00:00",
            "end": "2026-01-02T00:00:00+00:00",
            "timezone": "UTC",
        },
        "modules": {
            "activity": {
                "data": {
                    "hourly": [{"hour": 1, "count": 5}, {"hour": 2, "count": 3}],
                },
                "warnings": [],
            }
        },
        "metadata": {"warnings": [], "generated_at": "2026-01-01T00:00:00+00:00", "duration_sec": 1.2},
    }

    dashboard = build_dashboard_payload("a1", result)

    assert dashboard["schema_version"] == "2.1"
    assert dashboard["analysis_id"] == "a1"
    assert isinstance(dashboard["tabs"], list)
    assert isinstance(dashboard["widgets"], list)
    assert isinstance(dashboard["datasets"], dict)
    assert isinstance(dashboard["dataset_meta"], dict)
    assert any(widget["type"] == "chart" for widget in dashboard["widgets"])
    chart = next(widget for widget in dashboard["widgets"] if widget["type"] == "chart")
    assert chart["chart_config"]["x"] != chart["chart_config"]["y"]


def test_dashboard_builder_skips_table_only_dataset_chart():
    result = {
        "summary": {"total_messages": 2, "participants": 2, "start": None, "end": None, "timezone": "UTC"},
        "modules": {
            "dialog": {
                "data": {
                    "sessions": [
                        {
                            "session_id": 1,
                            "start_time": "2025-01-01T00:00:00+00:00",
                            "end_time": "2025-01-01T00:10:00+00:00",
                            "duration_min": 10,
                            "message_count": 4,
                            "initiator": "Alice",
                        }
                    ]
                },
                "warnings": [],
            }
        },
        "metadata": {"warnings": [], "generated_at": "2026-01-01T00:00:00+00:00", "duration_sec": 1.2},
    }

    dashboard = build_dashboard_payload("a1", result)
    assert any(widget["id"].startswith("dialog_sessions_table") for widget in dashboard["widgets"])
    assert not any(widget["id"].startswith("dialog_sessions_chart") for widget in dashboard["widgets"])
