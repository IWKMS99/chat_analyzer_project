from __future__ import annotations

from typing import Any

from chat_analyzer_api.services.dashboard.charts import (
    build_chart_definition,
    infer_dataset_meta,
    infer_table_config,
)


def build_dashboard_payload(analysis_id: str, analysis_result: dict[str, Any]) -> dict[str, Any]:
    summary = analysis_result.get("summary", {}) if isinstance(analysis_result, dict) else {}
    modules = analysis_result.get("modules", {}) if isinstance(analysis_result, dict) else {}
    metadata = analysis_result.get("metadata", {}) if isinstance(analysis_result, dict) else {}

    tabs: list[dict[str, Any]] = [
        {
            "id": "overview",
            "title": "Overview",
            "order": 0,
            "layout": "masonry",
            "default_open_sections": ["highlights"],
        }
    ]
    widgets: list[dict[str, Any]] = []
    datasets: dict[str, list[dict[str, Any]]] = {}
    dataset_meta: dict[str, dict[str, Any]] = {}

    for idx, module_name in enumerate(sorted(modules.keys()), start=1):
        module_payload = modules.get(module_name)
        if not isinstance(module_payload, dict):
            continue

        tab_id = _slug(module_name)
        tabs.append(
            {
                "id": tab_id,
                "title": _title(module_name),
                "order": idx,
                "layout": "two-column",
                "default_open_sections": ["charts"],
            }
        )

        data = module_payload.get("data", {})
        if not isinstance(data, dict):
            continue

        warnings = module_payload.get("warnings", [])
        if isinstance(warnings, list) and warnings:
            widgets.append(
                {
                    "id": f"{tab_id}_warnings",
                    "tab_id": tab_id,
                    "type": "text",
                    "title": "Warnings",
                    "priority": 1,
                    "section": "alerts",
                    "collapsed_by_default": False,
                    "text": "\n".join([str(item) for item in warnings]),
                    "severity": "warning",
                }
            )

        for key, value in data.items():
            if (module_name, key) in _SUPPRESSED_DATASETS:
                continue

            if not isinstance(value, list):
                _append_scalar_widgets(widgets, tab_id, module_name, key, value)
                continue

            rows = [row for row in value if isinstance(row, dict)]
            dataset_name = f"{tab_id}_{_slug(key)}_ds"
            datasets[dataset_name] = rows

            chart_definition = None
            if (module_name, key) not in _TABLE_ONLY_DATASETS:
                chart_definition = build_chart_definition(module_name=module_name, key=key, dataset_name=dataset_name, rows=rows)
            if chart_definition is not None:
                widgets.append(
                    {
                        "id": f"{tab_id}_{_slug(key)}_chart",
                        "tab_id": tab_id,
                        "type": "chart",
                        "title": _title(key),
                        "priority": 10,
                        "section": "charts",
                        "collapsed_by_default": False,
                        "dataset": dataset_name,
                        "vega_lite_spec": chart_definition.spec,
                        "chart_config": chart_definition.chart_config,
                        "empty_state": "Not enough data for chart",
                    }
                )

            table_config = infer_table_config(rows)
            widgets.append(
                {
                    "id": f"{tab_id}_{_slug(key)}_table",
                    "tab_id": tab_id,
                    "type": "table",
                    "title": f"{_title(key)} Data",
                    "priority": 20,
                    "section": "tables",
                    "collapsed_by_default": True,
                    "dataset": dataset_name,
                    "table_config": table_config,
                    "empty_state": "No rows available",
                }
            )

            recommended_widget = "table"
            semantic_kind = "table"
            if chart_definition is not None:
                semantic_kind = chart_definition.semantic_kind
                recommended_widget = "both"
            dataset_meta[dataset_name] = infer_dataset_meta(
                rows=rows,
                semantic_kind=semantic_kind,
                recommended_widget=recommended_widget,
            )

    output_metadata = metadata if isinstance(metadata, dict) else {}
    output_metadata.setdefault("warnings", [])

    return {
        "schema_version": "2.1",
        "analysis_id": analysis_id,
        "summary": summary if isinstance(summary, dict) else {},
        "tabs": sorted(tabs, key=lambda item: item["order"]),
        "widgets": sorted(widgets, key=lambda item: (item.get("tab_id", ""), item.get("priority", 100), item.get("id", ""))),
        "datasets": datasets,
        "dataset_meta": dataset_meta,
        "metadata": output_metadata,
    }


def _append_scalar_widgets(widgets: list[dict[str, Any]], tab_id: str, module_name: str, key: str, value: Any) -> None:
    if isinstance(value, (int, float, str)):
        if not _is_allowed_scalar_kpi(module_name, key, None):
            return
        widgets.append(
            {
                "id": f"{tab_id}_{_slug(key)}_kpi",
                "tab_id": tab_id,
                "type": "kpi",
                "title": _title(key),
                "priority": 5,
                "section": "highlights",
                "collapsed_by_default": False,
                "value": value,
                "format": "number" if isinstance(value, (int, float)) else "text",
                "severity": "info",
            }
        )
        return

    if isinstance(value, dict):
        for sub_key, sub_value in value.items():
            if isinstance(sub_value, (int, float, str)):
                if not _is_allowed_scalar_kpi(module_name, key, sub_key):
                    continue
                widgets.append(
                    {
                        "id": f"{tab_id}_{_slug(key)}_{_slug(sub_key)}_kpi",
                        "tab_id": tab_id,
                        "type": "kpi",
                        "title": _title(f"{key} {sub_key}"),
                        "priority": 5,
                        "section": "highlights",
                        "collapsed_by_default": False,
                        "value": sub_value,
                        "format": "number" if isinstance(sub_value, (int, float)) else "text",
                        "severity": "info",
                    }
                )


def _slug(value: str) -> str:
    out = "".join(ch if ch.isalnum() else "_" for ch in value.strip().lower())
    out = "_".join(part for part in out.split("_") if part)
    return out or "item"


def _title(value: str) -> str:
    return value.replace("_", " ").strip().title()


def _is_allowed_scalar_kpi(module_name: str, key: str, sub_key: str | None) -> bool:
    return (module_name, key, sub_key) in _ALLOWED_SCALAR_KPIS


_TABLE_ONLY_DATASETS = {
    ("dialog", "sessions"),
}

_SUPPRESSED_DATASETS = {
    ("user", "avg_length"),
    ("user", "message_counts"),
    ("temporal", "daily_df"),
    ("anomaly", "anomalies"),
    ("social", "reply_edges"),
}

_ALLOWED_SCALAR_KPIS: set[tuple[str, str, str | None]] = {
    ("temporal", "avg_response_min", None),
    ("anomaly", "metrics", "mode"),
    ("anomaly", "metrics", "threshold"),
    ("anomaly", "metrics", "robust_count"),
    ("anomaly", "metrics", "zscore_count"),
}
