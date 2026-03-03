from __future__ import annotations

import pytest

from chat_analyzer_api.services.dashboard.charts import build_chart_definition


def test_activity_hourly_uses_fold_and_non_identity_axes():
    rows = [
        {"hour": 0, "Alice": 1, "Bob": 2},
        {"hour": 1, "Alice": 0, "Bob": 3},
    ]
    chart = build_chart_definition("activity", "hourly", "activity_hourly_ds", rows)

    assert chart is not None
    assert chart.chart_config["x"] == "hour"
    assert chart.chart_config["y"] == "value"
    transforms = chart.spec.get("transform", [])
    assert any("fold" in transform for transform in transforms)


def test_day_of_week_is_ordinal_not_temporal():
    rows = [{"day_of_week": "Wednesday", "Alice": 2, "Bob": 1}]
    chart = build_chart_definition("activity", "weekday", "activity_weekday_ds", rows)

    assert chart is not None
    x = chart.spec["encoding"]["x"]
    assert x["type"] == "ordinal"


def test_temporal_response_uses_count_not_identity_line():
    rows = [{"response_min": 40, "count": 1}, {"response_min": 50, "count": 2}]
    chart = build_chart_definition("temporal", "response_df", "temporal_response_df_ds", rows)

    assert chart is not None
    assert chart.chart_config["x"] == "response_min"
    assert chart.chart_config["y"] == "count"
    assert chart.spec["mark"]["type"] == "bar"


def test_fallback_refuses_invalid_identity_chart():
    rows = [{"value": 1}, {"value": 2}]
    chart = build_chart_definition("unknown", "unknown", "unknown_ds", rows)
    assert chart is None


@pytest.mark.parametrize(
    ("module_name", "key", "rows", "x_field", "y_field", "chart_kind", "semantic_kind"),
    [
        ("user", "message_counts", [{"from": "Alice", "count": 4}], "from", "count", "bar", "categorical_breakdown"),
        ("user", "avg_length", [{"from": "Alice", "avg_text_length": 18.5}], "from", "avg_text_length", "bar", "categorical_breakdown"),
        (
            "user",
            "chains",
            [{"from": "Alice", "avg_chain": 2.2, "median_chain": 2.0, "max_chain": 6}],
            "from",
            "value",
            "bar",
            "categorical_breakdown",
        ),
        (
            "message",
            "lengths",
            [{"from": "Alice", "mean": 10.0, "median": 8.0, "p95": 24.0}],
            "from",
            "value",
            "bar",
            "distribution",
        ),
        (
            "message",
            "question_ratio",
            [{"from": "Alice", "questions": 3, "total": 10, "ratio": 0.3}],
            "from",
            "ratio",
            "bar",
            "categorical_breakdown",
        ),
        ("nlp", "keywords", [{"word": "hello", "count": 5}], "word", "count", "bar", "distribution"),
        (
            "nlp",
            "vocabulary",
            [{"from": "Alice", "total_words": 120, "unique_words": 65, "lexical_diversity": 0.54}],
            "from",
            "lexical_diversity",
            "bar",
            "categorical_breakdown",
        ),
        ("nlp", "emoji", [{"emoji": ":)", "count": 8}], "emoji", "count", "bar", "categorical_breakdown"),
        (
            "social",
            "reactions_received",
            [{"from": "Alice", "reactions_count": 7}],
            "from",
            "reactions_count",
            "bar",
            "categorical_breakdown",
        ),
        (
            "social",
            "edited",
            [{"from": "Alice", "edited_ratio": 0.1}],
            "from",
            "value",
            "bar",
            "categorical_breakdown",
        ),
        (
            "anomaly",
            "anomalies",
            [{"date_only": "2026-01-01", "count": 3, "robust_score": 2.3}],
            "date_only",
            "count",
            "line",
            "time_series",
        ),
    ],
)
def test_registry_uses_explicit_semantic_builders_for_known_datasets(
    module_name: str,
    key: str,
    rows: list[dict[str, object]],
    x_field: str,
    y_field: str,
    chart_kind: str,
    semantic_kind: str,
):
    chart = build_chart_definition(module_name, key, f"{module_name}_{key}_ds", rows)

    assert chart is not None
    assert chart.semantic_kind == semantic_kind
    assert chart.semantic_kind != "fallback"
    assert chart.chart_config["x"] == x_field
    assert chart.chart_config["y"] == y_field
    assert chart.chart_config["kind"] == chart_kind
