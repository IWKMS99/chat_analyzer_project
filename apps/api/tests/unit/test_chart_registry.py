from __future__ import annotations

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
