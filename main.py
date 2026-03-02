# === Standard library ===
import argparse
import logging
import os
import sys
import time
from typing import Dict, List, Set
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pandas as pd
from tzlocal import get_localzone_name

from chat_analyzer.analysis.aggregators import (
    ActivityAggregator,
    AnomalyAggregator,
    DialogAggregator,
    MessageAggregator,
    NlpAggregator,
    SocialAggregator,
    SummaryAggregator,
    TemporalAggregator,
    UserAggregator,
)
from chat_analyzer.data_loader import DataLoadError, EmptyDataError, InvalidSchemaError, iter_chat_chunks
from chat_analyzer.plotting.activity import build_activity_plots
from chat_analyzer.plotting.anomaly import build_anomaly_plots
from chat_analyzer.plotting.dialog import build_dialog_plots
from chat_analyzer.plotting.message import build_message_plots
from chat_analyzer.plotting.nlp import build_nlp_plots
from chat_analyzer.plotting.social import build_social_plots
from chat_analyzer.plotting.temporal import build_temporal_plots
from chat_analyzer.plotting.user import build_user_plots
from chat_analyzer.reporting import write_reports
from chat_analyzer.utils import ensure_dir, setup_logging

logger = logging.getLogger(__name__)

ALL_MODULES = ["summary", "activity", "temporal", "user", "message", "dialog", "nlp", "anomaly", "social"]
QUICK_MODULES = ["summary", "activity", "user", "message", "anomaly"]


class RunContext:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.chart_artifacts: Dict[str, Dict[str, str | None]] = {}
        self.extra_artifacts: Dict[str, str] = {}

    def add_artifacts(self, artifacts: Dict[str, object]) -> None:
        for key, artifact in artifacts.items():
            if artifact is None:
                continue
            self.chart_artifacts[key] = {
                "html_path": getattr(artifact, "html_path", None),
                "png_path": getattr(artifact, "png_path", None),
            }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Анализатор JSON экспорта чатов Telegram (stream-first).")

    io_group = parser.add_argument_group("Input/Output")
    io_group.add_argument("input_file", type=str, help="Путь к входному JSON файлу.")
    io_group.add_argument("-o", "--output-dir", type=str, default="output", help="Директория результатов.")
    io_group.add_argument("--skip-plots", action="store_true", help="Не сохранять графики.")
    io_group.add_argument("--disable-interactive", action="store_true", help="Не сохранять HTML-графики.")

    time_group = parser.add_argument_group("Time & Locale")
    time_group.add_argument(
        "-tz",
        "--timezone",
        type=str,
        default=get_localzone_name(),
        help="Временная зона для представления данных (default: local system timezone).",
    )

    analysis_group = parser.add_argument_group("Analysis")
    analysis_group.add_argument("--profile", type=str, default="full", choices=["quick", "full"])
    analysis_group.add_argument("--modules", nargs="+", choices=ALL_MODULES, help="Явный список модулей.")
    analysis_group.add_argument("--max-legend", type=int, default=10)
    analysis_group.add_argument("--anomaly-threshold", type=float, default=2.0)
    analysis_group.add_argument("--anomaly-mode", type=str, default="robust", choices=["robust", "zscore", "both"])
    analysis_group.add_argument("--response-time-limit", type=float, default=60.0)
    analysis_group.add_argument("--session-gap", type=float, default=30.0)

    nlp_group = parser.add_argument_group("NLP")
    nlp_group.add_argument("--include-forwarded-nlp", action="store_true")

    reporting_group = parser.add_argument_group("Reporting")
    reporting_group.add_argument("--report-format", type=str, default="html", choices=["html", "json", "md", "all"])
    reporting_group.add_argument("--insights-top", type=int, default=10)

    perf_group = parser.add_argument_group("Performance")
    perf_group.add_argument("--chunk-size", type=int, default=50_000)
    perf_group.add_argument("--max-workers", type=int, default=None)
    perf_group.add_argument("-log", "--log-level", type=str, default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
    perf_group.add_argument("--log-file", action="store_true", help="Записывать логи в analysis.log")

    return parser.parse_args()


def resolve_modules(args: argparse.Namespace) -> List[str]:
    if args.modules:
        selected = []
        seen: Set[str] = set()
        for module in args.modules:
            if module not in seen:
                selected.append(module)
                seen.add(module)
        return selected
    if args.profile == "quick":
        return QUICK_MODULES
    return ALL_MODULES


def _localize_chunk(chunk: pd.DataFrame, timezone: str) -> pd.DataFrame:
    if chunk.empty:
        return chunk
    c = chunk.copy()
    try:
        c["date"] = c["date"].dt.tz_convert(timezone)
    except Exception:
        logger.warning("Некорректная timezone '%s', используется UTC.", timezone)
        c["date"] = c["date"].dt.tz_convert("UTC")
    c["date_only"] = c["date"].dt.date
    c["hour"] = c["date"].dt.hour.astype("int8")
    c["day_of_week"] = c["date"].dt.day_name().astype("category")
    return c


def _resolve_timezone(timezone: str) -> str:
    try:
        ZoneInfo(timezone)
        return timezone
    except (ZoneInfoNotFoundError, ValueError):
        logger.warning("Timezone '%s' не найдена. Используется UTC.", timezone)
        return "UTC"


def main() -> None:
    start_time = time.time()
    args = parse_args()

    ensure_dir(args.output_dir)
    log_filepath = os.path.join(args.output_dir, "analysis.log") if args.log_file else None
    setup_logging(log_level=args.log_level, log_file=log_filepath)

    selected_modules = resolve_modules(args)
    resolved_timezone = _resolve_timezone(args.timezone)
    logger.info("Запуск stream-анализа: %s", ", ".join(selected_modules))

    summary = SummaryAggregator()
    activity = ActivityAggregator()
    temporal = TemporalAggregator(response_limit_minutes=args.response_time_limit)
    user = UserAggregator()
    message = MessageAggregator()
    dialog = DialogAggregator(response_limit_minutes=args.response_time_limit, session_gap_minutes=args.session_gap)
    nlp = NlpAggregator(include_forwarded=args.include_forwarded_nlp, max_workers=args.max_workers)
    anomaly = AnomalyAggregator(threshold=args.anomaly_threshold, mode=args.anomaly_mode)
    social = SocialAggregator()

    try:
        got_any = False
        for chunk in iter_chat_chunks(args.input_file, chunk_size=args.chunk_size):
            got_any = True
            chunk = _localize_chunk(chunk, resolved_timezone)

            summary.update(chunk)
            if "activity" in selected_modules:
                activity.update(chunk)
            if "temporal" in selected_modules:
                temporal.update(chunk)
            if "user" in selected_modules:
                user.update(chunk)
            if "message" in selected_modules:
                message.update(chunk)
            if "dialog" in selected_modules:
                dialog.update(chunk)
            if "nlp" in selected_modules:
                nlp.update(chunk)
            if "anomaly" in selected_modules:
                anomaly.update(chunk)
            if "social" in selected_modules:
                social.update(chunk)

        if not got_any:
            raise EmptyDataError("Нет данных для анализа.")

    except EmptyDataError as exc:
        logger.critical("Нет данных для анализа: %s", exc)
        sys.exit(1)
    except InvalidSchemaError as exc:
        logger.critical("Некорректная структура входного JSON: %s", exc)
        sys.exit(1)
    except DataLoadError as exc:
        logger.critical("Ошибка загрузки данных: %s", exc)
        sys.exit(1)
    except Exception as exc:  # pragma: no cover
        logger.critical("Неожиданная ошибка: %s", exc, exc_info=True)
        sys.exit(1)

    ctx = RunContext(args)
    module_results: Dict[str, Dict] = {}

    core = summary.result()
    module_results["summary"] = {
        "metrics": {
            "total_messages": core.total_messages,
            "participants": core.participants,
            "start": core.start,
            "end": core.end,
        },
        "artifacts": {},
        "warnings": [],
    }

    if not args.skip_plots and "activity" in selected_modules:
        activity_data = activity.result()
        arts = build_activity_plots(activity_data, args.output_dir, args.max_legend, args.disable_interactive)
        ctx.add_artifacts(arts)
        module_results["activity"] = {"metrics": {"participants": core.participants}, "artifacts": {}, "warnings": []}

    if not args.skip_plots and "temporal" in selected_modules:
        temporal_data = temporal.result()
        arts = build_temporal_plots(temporal_data, args.output_dir, args.disable_interactive)
        ctx.add_artifacts(arts)
        module_results["temporal"] = {
            "metrics": {"avg_response_minutes": round(float(temporal_data.get("avg_response_min", 0.0)), 3)},
            "artifacts": {},
            "warnings": [],
        }

    if not args.skip_plots and "user" in selected_modules:
        user_data = user.result()
        arts = build_user_plots(user_data, args.output_dir, args.max_legend, args.disable_interactive)
        ctx.add_artifacts(arts)
        module_results["user"] = {"metrics": {}, "artifacts": {}, "warnings": []}

    if not args.skip_plots and "message" in selected_modules:
        msg_data = message.result()
        arts = build_message_plots(msg_data, args.output_dir, args.max_legend, args.disable_interactive)
        ctx.add_artifacts(arts)
        module_results["message"] = {"metrics": {}, "artifacts": {}, "warnings": []}

    if not args.skip_plots and "dialog" in selected_modules:
        dialog_data = dialog.result()
        arts = build_dialog_plots(dialog_data, args.output_dir, args.disable_interactive)
        ctx.add_artifacts(arts)
        reply_edges_count = int(dialog_data.get("reply_edges", pd.DataFrame()).get("count", pd.Series(dtype=int)).sum())
        module_results["dialog"] = {
            "metrics": {
                "reply_edges": reply_edges_count,
                "sessions_for_timeline": int(len(dialog_data.get("sessions", pd.DataFrame()))),
            },
            "artifacts": {},
            "warnings": [],
        }

    if not args.skip_plots and "nlp" in selected_modules:
        nlp_data = nlp.result()
        arts = build_nlp_plots(nlp_data, args.output_dir, args.disable_interactive)
        ctx.add_artifacts(arts)
        sentiment_mean = 0.0
        sent_user = nlp_data.get("sentiment_user", pd.DataFrame())
        if not sent_user.empty:
            sentiment_mean = float(sent_user["sentiment_mean"].mean())
        module_results["nlp"] = {
            "metrics": {
                "keywords_unique": int(len(nlp_data.get("keywords", pd.DataFrame()))),
                "sentiment_mean": round(sentiment_mean, 4),
            },
            "artifacts": {},
            "warnings": [],
        }

    if not args.skip_plots and "anomaly" in selected_modules:
        anomaly_data = anomaly.result()
        arts = build_anomaly_plots(anomaly_data, args.output_dir, args.disable_interactive)
        ctx.add_artifacts(arts)
        module_results["anomaly"] = {
            "metrics": anomaly_data.get("metrics", {}),
            "artifacts": {},
            "warnings": [],
        }

    if not args.skip_plots and "social" in selected_modules:
        social_data = social.result()
        arts, extra = build_social_plots(social_data, args.output_dir, args.disable_interactive)
        ctx.add_artifacts(arts)
        ctx.extra_artifacts.update(extra)
        social_reply_edges = social_data.get("reply_edges", pd.DataFrame())
        if not social_reply_edges.empty:
            unique_users = pd.concat(
                [
                    social_reply_edges.get("from", pd.Series(dtype=object)),
                    social_reply_edges.get("to", pd.Series(dtype=object)),
                ],
                ignore_index=True,
            )
            unique_users = unique_users.dropna().astype(str)
            social_nodes = int(unique_users[unique_users.str.strip() != ""].nunique())
        else:
            social_nodes = 0
        module_results["social"] = {
            "metrics": {
                "reaction_edges": int(social_data.get("reaction_edges", pd.DataFrame()).get("count", pd.Series(dtype=int)).sum()),
                "social_nodes": social_nodes,
            },
            "artifacts": {},
            "warnings": [],
        }

    summary_payload = {
        "total_messages": core.total_messages,
        "participants": core.participants,
        "start": core.start,
        "end": core.end,
        "timezone": resolved_timezone,
    }

    report_paths = write_reports(
        output_dir=args.output_dir,
        report_format=args.report_format,
        summary=summary_payload,
        module_results=module_results,
        chart_paths=ctx.chart_artifacts,
        extra_artifacts=ctx.extra_artifacts,
        insights_top=args.insights_top,
    )
    if report_paths:
        logger.info("Отчеты сохранены: %s", report_paths)

    elapsed = time.time() - start_time
    logger.info("Анализ завершен за %.2f секунд.", elapsed)


if __name__ == "__main__":
    main()
