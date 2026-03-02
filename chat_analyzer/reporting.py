# === Standard library ===
import json
import logging
import os
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Dict, List

# === Third-party ===
import pandas as pd
from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"


def _json_default(obj: Any):
    if isinstance(obj, (pd.Timestamp,)):
        return obj.isoformat()
    if isinstance(obj, (pd.Series, pd.DataFrame)):
        return obj.to_dict()
    if is_dataclass(obj):
        return asdict(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def _create_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )


def build_top_insights(summary: Dict[str, Any], module_results: Dict[str, Dict[str, Any]], top_n: int = 10) -> List[Dict[str, str]]:
    insights: List[Dict[str, str]] = []

    total = int(summary.get("total_messages", 0))
    participants = int(summary.get("participants", 0))
    if total > 0:
        insights.append(
            {
                "title": "Средняя активность на участника",
                "value": f"{(total / max(participants, 1)):.1f}",
                "evidence": f"{total} сообщений / {participants} участников",
            }
        )

    dialog_metrics = module_results.get("dialog", {}).get("metrics", {})
    if dialog_metrics:
        insights.append(
            {
                "title": "Reply edges",
                "value": str(dialog_metrics.get("reply_edges", 0)),
                "evidence": "Число ответных взаимодействий между разными авторами",
            }
        )

    anomaly_metrics = module_results.get("anomaly", {}).get("metrics", {})
    if anomaly_metrics:
        insights.append(
            {
                "title": "Аномалии",
                "value": f"robust={anomaly_metrics.get('robust_count', 0)}, zscore={anomaly_metrics.get('zscore_count', 0)}",
                "evidence": f"threshold={anomaly_metrics.get('threshold', 'n/a')}",
            }
        )

    nlp_metrics = module_results.get("nlp", {}).get("metrics", {})
    if nlp_metrics:
        insights.append(
            {
                "title": "Sentiment",
                "value": str(nlp_metrics.get("sentiment_mean", 0.0)),
                "evidence": "Средний sentiment score по сообщениям",
            }
        )

    return insights[:top_n]


def _load_chart_embeds(chart_paths: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    charts = []
    for name, payload in chart_paths.items():
        html_path = payload.get("html_path")
        html_embed = None
        if html_path and os.path.exists(html_path):
            try:
                with open(html_path, encoding="utf-8") as f:
                    html_embed = f.read()
            except Exception:
                html_embed = None
        charts.append(
            {
                "name": name,
                "html_path": html_path,
                "png_path": payload.get("png_path"),
                "html_embed": html_embed,
            }
        )
    return charts


def write_reports(
    output_dir: str,
    report_format: str,
    summary: Dict[str, Any],
    module_results: Dict[str, Dict[str, Any]],
    chart_paths: Dict[str, Dict[str, Any]],
    extra_artifacts: Dict[str, str],
    insights_top: int = 10,
) -> Dict[str, str]:
    os.makedirs(output_dir, exist_ok=True)
    report_format = (report_format or "html").lower()
    if report_format not in {"html", "json", "md", "all"}:
        logger.warning("Неизвестный report-format '%s', используется html.", report_format)
        report_format = "html"

    env = _create_env()
    insights = build_top_insights(summary=summary, module_results=module_results, top_n=insights_top)
    charts = _load_chart_embeds(chart_paths)

    context = {
        "summary": summary,
        "modules": module_results,
        "insights": insights,
        "charts": charts,
        "extra_artifacts": extra_artifacts,
    }

    written: Dict[str, str] = {}
    if report_format in {"html", "all"}:
        tpl = env.get_template("report.html.j2")
        html_path = os.path.join(output_dir, "report.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(tpl.render(**context))
        written["html"] = html_path

    if report_format in {"md", "all"}:
        tpl = env.get_template("report.md.j2")
        md_path = os.path.join(output_dir, "report.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(tpl.render(**context))
        written["md"] = md_path

    if report_format in {"json", "all"}:
        json_path = os.path.join(output_dir, "report.json")
        payload = {
            "summary": summary,
            "insights": insights,
            "modules": module_results,
            "charts": chart_paths,
            "extra_artifacts": extra_artifacts,
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2, default=_json_default)
        written["json"] = json_path

    return written
