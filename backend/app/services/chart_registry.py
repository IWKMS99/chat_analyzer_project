from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


DatasetRows = list[dict[str, Any]]


@dataclass(frozen=True)
class ChartDefinition:
    spec: dict[str, Any]
    chart_config: dict[str, Any]
    semantic_kind: str


def build_chart_definition(module_name: str, key: str, dataset_name: str, rows: DatasetRows) -> ChartDefinition | None:
    if not rows:
        return None

    builder = _REGISTRY.get((module_name, key))
    if builder is not None:
        return builder(dataset_name, rows)

    return _fallback_chart(dataset_name, rows)


def infer_table_config(rows: DatasetRows) -> dict[str, Any]:
    columns = list(rows[0].keys()) if rows else []
    return {
        "columns": columns,
        "default_limit": 25,
        "sortable": True,
        "format": _column_formatters(columns),
    }


def infer_dataset_meta(rows: DatasetRows, semantic_kind: str, recommended_widget: str) -> dict[str, Any]:
    columns = list(rows[0].keys()) if rows else []
    return {
        "row_count": len(rows),
        "columns": [{"name": column, "kind": _infer_kind(column, rows[0].get(column) if rows else None)} for column in columns],
        "semantic_kind": semantic_kind,
        "recommended_widget": recommended_widget,
    }


def _chart(
    dataset_name: str,
    mark: str,
    x_field: str,
    x_type: str,
    y_field: str,
    y_type: str = "quantitative",
    *,
    color_field: str | None = None,
    color_type: str = "nominal",
    tooltip_fields: list[str] | None = None,
    transforms: list[dict[str, Any]] | None = None,
    sort: Any | None = None,
    semantic_kind: str,
    chart_kind: str,
) -> ChartDefinition:
    encoding: dict[str, Any] = {
        "x": {"field": x_field, "type": x_type},
        "y": {"field": y_field, "type": y_type},
    }
    if sort is not None:
        encoding["x"]["sort"] = sort
    if color_field:
        encoding["color"] = {"field": color_field, "type": color_type}

    tooltip = [{"field": field} for field in (tooltip_fields or [x_field, y_field])]

    spec: dict[str, Any] = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "data": {"name": dataset_name},
        "mark": {"type": mark},
        "encoding": {**encoding, "tooltip": tooltip},
        "height": 300,
        "width": "container",
    }
    if mark in {"line", "area"}:
        spec["mark"]["point"] = True
    if transforms:
        spec["transform"] = transforms

    chart_config = {
        "kind": chart_kind,
        "x": x_field,
        "y": y_field,
        "series": color_field,
        "aggregation": None,
        "formatters": _chart_formatters(x_field, y_field),
    }
    return ChartDefinition(spec=spec, chart_config=chart_config, semantic_kind=semantic_kind)


def _activity_wide_line(dataset_name: str, rows: DatasetRows, x_field: str, x_type: str, *, sort: Any | None = None) -> ChartDefinition:
    first = rows[0]
    value_columns = [column for column in first.keys() if column != x_field]
    if not value_columns:
        return _fallback_chart(dataset_name, rows) or _chart(dataset_name, "bar", x_field, x_type, x_field, semantic_kind="distribution", chart_kind="bar")

    return _chart(
        dataset_name,
        mark="line",
        x_field=x_field,
        x_type=x_type,
        y_field="value",
        color_field="series",
        tooltip_fields=[x_field, "series", "value"],
        transforms=[{"fold": value_columns, "as": ["series", "value"]}],
        sort=sort,
        semantic_kind="time_series",
        chart_kind="line",
    )


def _activity_wide_bar(dataset_name: str, rows: DatasetRows, x_field: str, x_type: str, *, sort: Any | None = None) -> ChartDefinition:
    first = rows[0]
    value_columns = [column for column in first.keys() if column != x_field]
    if not value_columns:
        return _fallback_chart(dataset_name, rows) or _chart(dataset_name, "bar", x_field, x_type, x_field, semantic_kind="distribution", chart_kind="bar")

    return _chart(
        dataset_name,
        mark="bar",
        x_field=x_field,
        x_type=x_type,
        y_field="value",
        color_field="series",
        tooltip_fields=[x_field, "series", "value"],
        transforms=[{"fold": value_columns, "as": ["series", "value"]}],
        sort=sort,
        semantic_kind="categorical_breakdown",
        chart_kind="bar",
    )


def _chart_activity_hourly(dataset_name: str, rows: DatasetRows) -> ChartDefinition:
    return _activity_wide_line(dataset_name, rows, "hour", "ordinal")


def _chart_activity_weekday(dataset_name: str, rows: DatasetRows) -> ChartDefinition:
    return _activity_wide_bar(
        dataset_name,
        rows,
        "day_of_week",
        "ordinal",
        sort=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
    )


def _chart_activity_monthly(dataset_name: str, rows: DatasetRows) -> ChartDefinition:
    return _activity_wide_line(dataset_name, rows, "month", "ordinal")


def _chart_activity_periods(dataset_name: str, rows: DatasetRows) -> ChartDefinition:
    return _activity_wide_bar(dataset_name, rows, "period", "nominal")


def _chart_temporal_response(dataset_name: str, rows: DatasetRows) -> ChartDefinition:
    return _chart(dataset_name, "bar", "response_min", "quantitative", "count", semantic_kind="distribution", chart_kind="histogram")


def _chart_temporal_interval(dataset_name: str, rows: DatasetRows) -> ChartDefinition:
    return _chart(dataset_name, "bar", "interval_sec", "quantitative", "count", semantic_kind="distribution", chart_kind="histogram")


def _chart_temporal_daily(dataset_name: str, rows: DatasetRows) -> ChartDefinition:
    return _chart(dataset_name, "line", "date_only", "temporal", "count", semantic_kind="time_series", chart_kind="line")


def _chart_user_daily_by_user(dataset_name: str, rows: DatasetRows) -> ChartDefinition:
    return _chart(
        dataset_name,
        "line",
        "date_only",
        "temporal",
        "count",
        color_field="from",
        tooltip_fields=["date_only", "from", "count"],
        semantic_kind="time_series",
        chart_kind="line",
    )


def _chart_message_short_long_hourly(dataset_name: str, rows: DatasetRows) -> ChartDefinition:
    return _chart(
        dataset_name,
        "bar",
        "hour",
        "ordinal",
        "count",
        color_field="message_type",
        tooltip_fields=["hour", "from", "message_type", "count"],
        semantic_kind="categorical_breakdown",
        chart_kind="bar",
    )


def _chart_dialog_hour_median(dataset_name: str, rows: DatasetRows) -> ChartDefinition:
    return _chart(
        dataset_name,
        "line",
        "hour",
        "ordinal",
        "median_gap",
        color_field="from",
        tooltip_fields=["hour", "from", "median_gap"],
        semantic_kind="time_series",
        chart_kind="line",
    )


def _chart_dialog_reply_edges(dataset_name: str, rows: DatasetRows) -> ChartDefinition:
    return _chart(
        dataset_name,
        "bar",
        "from",
        "nominal",
        "count",
        color_field="prev_from",
        tooltip_fields=["from", "prev_from", "count"],
        semantic_kind="network_edges",
        chart_kind="bar",
    )


def _chart_dialog_pair_median(dataset_name: str, rows: DatasetRows) -> ChartDefinition:
    return _chart(
        dataset_name,
        "bar",
        "from",
        "nominal",
        "median_gap",
        color_field="prev_from",
        tooltip_fields=["from", "prev_from", "median_gap"],
        semantic_kind="network_edges",
        chart_kind="bar",
    )


def _chart_social_reply_edges(dataset_name: str, rows: DatasetRows) -> ChartDefinition:
    return _chart(
        dataset_name,
        "bar",
        "from",
        "nominal",
        "count",
        color_field="to",
        tooltip_fields=["from", "to", "count"],
        semantic_kind="network_edges",
        chart_kind="bar",
    )


def _chart_nlp_sentiment_day(dataset_name: str, rows: DatasetRows) -> ChartDefinition:
    return _chart(dataset_name, "line", "date_only", "temporal", "sentiment_mean", semantic_kind="time_series", chart_kind="line")


def _chart_nlp_sentiment_user(dataset_name: str, rows: DatasetRows) -> ChartDefinition:
    return _chart(dataset_name, "bar", "from", "nominal", "sentiment_mean", semantic_kind="categorical_breakdown", chart_kind="bar")


def _chart_anomaly_daily(dataset_name: str, rows: DatasetRows) -> ChartDefinition:
    return _chart(dataset_name, "line", "date_only", "temporal", "count", semantic_kind="time_series", chart_kind="line")


def _fallback_chart(dataset_name: str, rows: DatasetRows) -> ChartDefinition | None:
    first = rows[0] if rows else {}
    columns = list(first.keys())
    numeric = [column for column in columns if isinstance(first.get(column), (int, float))]
    non_numeric = [column for column in columns if column not in numeric]

    if len(numeric) == 0:
        return None

    if non_numeric:
        x_field = non_numeric[0]
        y_field = numeric[0]
    elif len(numeric) >= 2:
        x_field, y_field = numeric[0], numeric[1]
    else:
        return None

    if x_field == y_field:
        return None

    x_kind = _infer_kind(x_field, first.get(x_field))
    x_type = "temporal" if x_kind == "temporal" else ("quantitative" if x_kind == "quantitative" else "nominal")
    mark = "line" if x_type in {"temporal", "quantitative"} else "bar"
    chart_kind = "line" if mark == "line" else "bar"

    return _chart(
        dataset_name,
        mark=mark,
        x_field=x_field,
        x_type=x_type,
        y_field=y_field,
        semantic_kind="fallback",
        chart_kind=chart_kind,
    )


def _column_formatters(columns: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for column in columns:
        lowered = column.lower()
        if "ratio" in lowered or "percent" in lowered:
            out[column] = "percent"
        elif "time" in lowered or "date" in lowered:
            out[column] = "datetime"
        elif "count" in lowered or "total" in lowered:
            out[column] = "integer"
    return out


def _chart_formatters(x_field: str, y_field: str) -> dict[str, str]:
    return {
        "x": "datetime" if _infer_kind(x_field, None) == "temporal" else "default",
        "y": "number",
    }


def _infer_kind(column: str, value: Any) -> str:
    lowered = column.lower()
    if lowered == "day_of_week":
        return "ordinal"
    if any(token in lowered for token in ["date", "time", "month"]):
        return "temporal"
    if isinstance(value, (int, float)):
        return "quantitative"
    if lowered in {"hour"}:
        return "ordinal"
    return "nominal"


_REGISTRY: dict[tuple[str, str], Callable[[str, DatasetRows], ChartDefinition]] = {
    ("activity", "hourly"): _chart_activity_hourly,
    ("activity", "weekday"): _chart_activity_weekday,
    ("activity", "monthly"): _chart_activity_monthly,
    ("activity", "periods"): _chart_activity_periods,
    ("temporal", "response_df"): _chart_temporal_response,
    ("temporal", "interval_df"): _chart_temporal_interval,
    ("temporal", "daily_df"): _chart_temporal_daily,
    ("user", "daily_by_user"): _chart_user_daily_by_user,
    ("message", "short_long_hourly"): _chart_message_short_long_hourly,
    ("dialog", "reply_edges"): _chart_dialog_reply_edges,
    ("dialog", "pair_median"): _chart_dialog_pair_median,
    ("dialog", "hour_median"): _chart_dialog_hour_median,
    ("social", "reply_edges"): _chart_social_reply_edges,
    ("nlp", "sentiment_day"): _chart_nlp_sentiment_day,
    ("nlp", "sentiment_user"): _chart_nlp_sentiment_user,
    ("anomaly", "daily"): _chart_anomaly_daily,
}
