from __future__ import annotations

from chat_analyzer_api.services.dashboard.builder import build_dashboard_payload


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


def test_dashboard_builder_uses_non_fallback_semantic_kind_for_explicit_registry_datasets():
    result = {
        "summary": {"total_messages": 8, "participants": 2, "start": None, "end": None, "timezone": "UTC"},
        "modules": {
            "user": {
                "data": {
                    "message_counts": [{"from": "Alice", "count": 5}],
                    "avg_length": [{"from": "Alice", "avg_text_length": 17.5}],
                    "chains": [{"from": "Alice", "avg_chain": 2.0, "median_chain": 2.0, "max_chain": 4.0}],
                },
                "warnings": [],
            },
            "temporal": {
                "data": {
                    "avg_response_min": 3.5,
                    "daily_df": [{"date_only": "2026-01-01", "count": 2}],
                },
                "warnings": [],
            },
            "message": {
                "data": {
                    "lengths": [{"from": "Alice", "mean": 12.0, "median": 10.0, "p95": 24.0}],
                    "question_ratio": [{"from": "Alice", "questions": 2, "total": 8, "ratio": 0.25}],
                },
                "warnings": [],
            },
            "nlp": {
                "data": {
                    "keywords": [{"word": "hello", "count": 5}],
                    "vocabulary": [{"from": "Alice", "total_words": 20, "unique_words": 12, "lexical_diversity": 0.6}],
                    "emoji": [{"emoji": ":)", "count": 4}],
                },
                "warnings": [],
            },
            "social": {
                "data": {
                    "reactions_received": [{"from": "Alice", "reactions_count": 3}],
                    "reply_edges": [{"from": "Alice", "to": "Bob", "count": 2}],
                    "edited": [{"from": "Alice", "edited_ratio": 0.1}],
                },
                "warnings": [],
            },
            "anomaly": {
                "data": {
                    "daily": [{"date_only": "2026-01-01", "count": 2, "robust_score": 3.0}],
                    "anomalies": [{"date_only": "2026-01-01", "count": 2, "robust_score": 3.0}],
                    "metrics": {"mode": "robust", "threshold": 2.0, "robust_count": 1, "zscore_count": 1},
                },
                "warnings": [],
            },
        },
        "metadata": {"warnings": [], "generated_at": "2026-01-01T00:00:00+00:00", "duration_sec": 1.2},
    }

    dashboard = build_dashboard_payload("a2", result)
    expected_semantics = {
        "user_chains_ds": "categorical_breakdown",
        "message_lengths_ds": "distribution",
        "message_question_ratio_ds": "categorical_breakdown",
        "nlp_keywords_ds": "distribution",
        "nlp_vocabulary_ds": "categorical_breakdown",
        "nlp_emoji_ds": "categorical_breakdown",
        "social_reactions_received_ds": "categorical_breakdown",
        "social_edited_ds": "categorical_breakdown",
        "anomaly_daily_ds": "time_series",
    }

    for dataset_id, semantic_kind in expected_semantics.items():
        assert dashboard["dataset_meta"][dataset_id]["semantic_kind"] == semantic_kind
        assert dashboard["dataset_meta"][dataset_id]["semantic_kind"] != "fallback"

    suppressed = {
        "user_message_counts_ds",
        "user_avg_length_ds",
        "temporal_daily_df_ds",
        "anomaly_anomalies_ds",
        "social_reply_edges_ds",
    }
    for dataset_id in suppressed:
        assert dataset_id not in dashboard["datasets"]
        assert dataset_id not in dashboard["dataset_meta"]

    kpi_ids = {widget["id"] for widget in dashboard["widgets"] if widget["type"] == "kpi"}
    assert not any(widget_id.startswith("kpi_") for widget_id in kpi_ids)
    assert {
        "temporal_avg_response_min_kpi",
        "anomaly_metrics_mode_kpi",
        "anomaly_metrics_threshold_kpi",
        "anomaly_metrics_robust_count_kpi",
        "anomaly_metrics_zscore_count_kpi",
    }.issubset(kpi_ids)
