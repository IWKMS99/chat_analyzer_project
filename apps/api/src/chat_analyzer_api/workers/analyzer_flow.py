from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Callable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pandas as pd

from chat_analyzer_core.aggregators import (
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
from chat_analyzer_core.data_loader import EmptyDataError, iter_chat_chunks

from chat_analyzer_api.core.serializers import dataframe_to_records

ProgressHook = Callable[[str, int, int | None], None]


def resolve_timezone(timezone_name: str) -> tuple[str, str | None]:
    try:
        ZoneInfo(timezone_name)
        return timezone_name, None
    except (ZoneInfoNotFoundError, ValueError):
        return "UTC", f"Invalid timezone '{timezone_name}', fallback to UTC"


def localize_chunk(chunk: pd.DataFrame, timezone_name: str) -> pd.DataFrame:
    if chunk.empty:
        return chunk
    out = chunk.copy()
    try:
        out["date"] = out["date"].dt.tz_convert(timezone_name)
    except (AttributeError, TypeError, ValueError, ZoneInfoNotFoundError):
        out["date"] = out["date"].dt.tz_convert("UTC")
    out["date_only"] = out["date"].dt.date
    out["hour"] = out["date"].dt.hour.astype("int8")
    out["day_of_week"] = out["date"].dt.day_name().astype("category")
    return out


def _serialize_activity(payload: dict[str, pd.DataFrame]) -> dict[str, list[dict]]:
    return {
        "hourly": dataframe_to_records(payload.get("hourly", pd.DataFrame()), include_index=True, index_name="hour"),
        "weekday": dataframe_to_records(payload.get("weekday", pd.DataFrame()), include_index=True, index_name="day_of_week"),
        "monthly": dataframe_to_records(payload.get("monthly", pd.DataFrame()), include_index=True, index_name="month"),
        "periods": dataframe_to_records(payload.get("periods", pd.DataFrame()), include_index=True, index_name="period"),
    }


def analyze_chat_file(file_path: str, timezone_name: str, progress_hook: ProgressHook | None = None) -> dict:
    start_ts = time.time()
    resolved_tz, tz_warning = resolve_timezone(timezone_name)

    summary = SummaryAggregator()
    activity = ActivityAggregator()
    temporal = TemporalAggregator()
    user = UserAggregator()
    message = MessageAggregator()
    dialog = DialogAggregator()
    nlp = NlpAggregator()
    anomaly = AnomalyAggregator()
    social = SocialAggregator()

    module_warnings: dict[str, list[str]] = {name: [] for name in [
        "activity",
        "temporal",
        "user",
        "message",
        "dialog",
        "nlp",
        "anomaly",
        "social",
    ]}
    if tz_warning:
        module_warnings["summary"] = [tz_warning]

    got_any = False
    nlp_enabled = True

    last_progress = -1
    analyzing_progress = 10

    def emit_progress(phase: str, progress_pct: int, eta_sec: int | None = None) -> None:
        nonlocal last_progress
        if not progress_hook:
            return
        normalized = max(0, min(progress_pct, 100))
        if normalized <= last_progress:
            return
        last_progress = normalized
        progress_hook(phase, normalized, eta_sec)

    def bump_analyzing(delta: int) -> None:
        nonlocal analyzing_progress
        analyzing_progress = min(85, analyzing_progress + max(1, delta))
        emit_progress("analyzing", analyzing_progress, None)

    emit_progress("parsing", 5, None)

    for chunk in iter_chat_chunks(file_path, chunk_size=50_000):
        got_any = True
        chunk = localize_chunk(chunk, resolved_tz)
        emit_progress("analyzing", analyzing_progress, None)

        summary.update(chunk)
        bump_analyzing(4)
        activity.update(chunk)
        bump_analyzing(5)
        temporal.update(chunk)
        bump_analyzing(5)
        user.update(chunk)
        bump_analyzing(5)
        message.update(chunk)
        bump_analyzing(5)
        dialog.update(chunk)
        bump_analyzing(5)
        anomaly.update(chunk)
        bump_analyzing(5)
        social.update(chunk)
        bump_analyzing(5)

        if nlp_enabled:
            try:
                nlp.update(chunk)
            except (RuntimeError, ValueError, TypeError, OSError) as exc:  # pragma: no cover - runtime guard
                nlp_enabled = False
                module_warnings["nlp"].append(f"NLP degraded: {type(exc).__name__}: {exc}")
        bump_analyzing(6)

    if not got_any:
        raise EmptyDataError("No messages available for analysis")

    emit_progress("serializing", 90, None)

    core = summary.result()
    emit_progress("serializing", 91, None)

    temporal_payload = temporal.result()
    user_payload = user.result()
    message_payload = message.result()
    dialog_payload = dialog.result()
    social_payload = social.result()
    emit_progress("serializing", 93, None)

    nlp_data = {
        "keywords": [],
        "vocabulary": [],
        "emoji": [],
        "sentiment_user": [],
        "sentiment_day": [],
    }
    if nlp_enabled:
        payload = nlp.result()
        nlp_data = {
            "keywords": dataframe_to_records(payload.get("keywords", pd.DataFrame())),
            "vocabulary": dataframe_to_records(payload.get("vocabulary", pd.DataFrame())),
            "emoji": dataframe_to_records(payload.get("emoji", pd.DataFrame())),
            "sentiment_user": dataframe_to_records(payload.get("sentiment_user", pd.DataFrame())),
            "sentiment_day": dataframe_to_records(payload.get("sentiment_day", pd.DataFrame())),
        }
    emit_progress("serializing", 94, None)

    anomaly_payload = anomaly.result()

    modules = {
        "activity": {
            "data": _serialize_activity(activity.result()),
            "warnings": module_warnings["activity"],
        },
        "temporal": {
            "data": {
                "avg_response_min": float(temporal_payload.get("avg_response_min", 0.0)),
                "response_df": dataframe_to_records(temporal_payload.get("response_df", pd.DataFrame())),
                "interval_df": dataframe_to_records(temporal_payload.get("interval_df", pd.DataFrame())),
                "daily_df": dataframe_to_records(temporal_payload.get("daily_df", pd.DataFrame()), include_index=True, index_name="date_only"),
            },
            "warnings": module_warnings["temporal"],
        },
        "user": {
            "data": {
                "message_counts": dataframe_to_records(user_payload.get("message_counts", pd.Series(dtype=int)).to_frame(name="count"), include_index=True, index_name="from"),
                "avg_length": dataframe_to_records(user_payload.get("avg_length", pd.Series(dtype=float)).to_frame(name="avg_text_length"), include_index=True, index_name="from"),
                "chains": dataframe_to_records(user_payload.get("chains", pd.DataFrame())),
                "daily_by_user": dataframe_to_records(user_payload.get("daily_by_user", pd.DataFrame())),
            },
            "warnings": module_warnings["user"],
        },
        "message": {
            "data": {
                "lengths": dataframe_to_records(message_payload.get("lengths", pd.DataFrame())),
                "question_ratio": dataframe_to_records(message_payload.get("question_ratio", pd.DataFrame())),
                "short_long_hourly": dataframe_to_records(message_payload.get("short_long_hourly", pd.DataFrame())),
            },
            "warnings": module_warnings["message"],
        },
        "dialog": {
            "data": {
                "reply_edges": dataframe_to_records(dialog_payload.get("reply_edges", pd.DataFrame())),
                "pair_median": dataframe_to_records(dialog_payload.get("pair_median", pd.DataFrame())),
                "hour_median": dataframe_to_records(dialog_payload.get("hour_median", pd.DataFrame())),
                "sessions": dataframe_to_records(dialog_payload.get("sessions", pd.DataFrame())),
            },
            "warnings": module_warnings["dialog"],
        },
        "nlp": {
            "data": nlp_data,
            "warnings": module_warnings["nlp"],
        },
        "anomaly": {
            "data": {
                "daily": dataframe_to_records(anomaly_payload.get("daily", pd.DataFrame()), include_index=True, index_name="date_only"),
                "anomalies": dataframe_to_records(anomaly_payload.get("anomalies", pd.DataFrame()), include_index=True, index_name="date_only"),
                "metrics": anomaly_payload.get("metrics", {}),
            },
            "warnings": module_warnings["anomaly"],
        },
        "social": {
            "data": {
                "reaction_edges": dataframe_to_records(social_payload.get("reaction_edges", pd.DataFrame())),
                "reply_edges": dataframe_to_records(social_payload.get("reply_edges", pd.DataFrame())),
                "edited_deleted": dataframe_to_records(social_payload.get("edited_deleted", pd.DataFrame())),
            },
            "warnings": module_warnings["social"],
        },
    }

    all_warnings: list[str] = []
    if tz_warning:
        all_warnings.append(tz_warning)
    for module_name, warns in module_warnings.items():
        for warning in warns:
            if module_name == "summary":
                all_warnings.append(warning)
            else:
                all_warnings.append(f"{module_name}: {warning}")

    result = {
        "summary": {
            "total_messages": int(core.total_messages),
            "participants": int(core.participants),
            "start": core.start.isoformat() if core.start is not None else None,
            "end": core.end.isoformat() if core.end is not None else None,
            "timezone": resolved_tz,
        },
        "modules": modules,
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "duration_sec": round(time.time() - start_ts, 3),
            "warnings": all_warnings,
        },
    }

    emit_progress("serializing", 95, 0)

    return result
