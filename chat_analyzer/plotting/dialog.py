import pandas as pd
import plotly.express as px

from chat_analyzer.plotting.base import PlotArtifact, apply_default_layout, finalize_plotly_figure

MAX_DIALOG_USERS = 50


def _trim_pair_edges(df: pd.DataFrame, max_users: int = MAX_DIALOG_USERS) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    clean = df.dropna(subset=["from", "prev_from", "count"]).copy()
    if clean.empty:
        return clean
    totals = (
        clean.groupby("from")["count"].sum().add(clean.groupby("prev_from")["count"].sum(), fill_value=0)
        .sort_values(ascending=False)
        .head(max_users)
        .index
    )
    return clean[clean["from"].isin(totals) & clean["prev_from"].isin(totals)]


def build_dialog_plots(data: dict, output_dir: str, disable_interactive: bool) -> dict[str, PlotArtifact]:
    artifacts: dict[str, PlotArtifact] = {}

    edges = data.get("reply_edges", pd.DataFrame())
    if not edges.empty:
        trimmed_edges = _trim_pair_edges(edges)
        if not trimmed_edges.empty:
            pivot = trimmed_edges.pivot(index="from", columns="prev_from", values="count").fillna(0)
            fig = px.imshow(pivot, text_auto=True, color_continuous_scale="YlGnBu", aspect="auto")
            apply_default_layout(fig, "Матрица ответов", "Кому отвечают", "Кто отвечает")
            artifacts["reply_matrix"] = finalize_plotly_figure(
                fig,
                "reply_matrix",
                f"{output_dir}/charts/reply_matrix.html",
                f"{output_dir}/charts/reply_matrix.png",
                disable_interactive,
            )

    pair = data.get("pair_median", pd.DataFrame())
    if not pair.empty:
        if {"from", "prev_from", "count"}.issubset(edges.columns):
            pair_with_counts = pair.merge(edges[["from", "prev_from", "count"]], on=["from", "prev_from"], how="left")
        else:
            pair_with_counts = pair.copy()
            pair_with_counts["count"] = 0
        trimmed_pair = _trim_pair_edges(pair_with_counts.fillna({"count": 0}))
        if not trimmed_pair.empty:
            pivot = trimmed_pair.pivot(index="from", columns="prev_from", values="median_gap").fillna(0.0)
            fig = px.imshow(pivot, text_auto=".1f", color_continuous_scale="Magma", aspect="auto")
            apply_default_layout(fig, "Медианное время ответа по парам", "Кому отвечают", "Кто отвечает")
            artifacts["response_pair_median"] = finalize_plotly_figure(
                fig,
                "response_pair_median",
                f"{output_dir}/charts/response_pair_median.html",
                f"{output_dir}/charts/response_pair_median.png",
                disable_interactive,
            )

    hour_median = data.get("hour_median", pd.DataFrame())
    if not hour_median.empty:
        pivot = hour_median.pivot(index="hour", columns="from", values="median_gap").fillna(0.0).reindex(range(24), fill_value=0.0)
        fig = px.imshow(pivot, color_continuous_scale="Viridis", aspect="auto")
        apply_default_layout(fig, "Медианное время ответа по часам", "Кто отвечает", "Час")
        artifacts["response_hour_median"] = finalize_plotly_figure(
            fig,
            "response_hour_median",
            f"{output_dir}/charts/response_hour_median.html",
            f"{output_dir}/charts/response_hour_median.png",
            disable_interactive,
        )

    sessions = data.get("sessions", pd.DataFrame())
    if not sessions.empty:
        fig = px.scatter(
            sessions,
            x="start_time",
            y="duration_min",
            size="message_count",
            color="initiator",
            hover_data=["session_id", "message_count"],
        )
        apply_default_layout(fig, "Таймлайн сессий", "Начало", "Длительность (мин)")
        artifacts["session_timeline"] = finalize_plotly_figure(
            fig,
            "session_timeline",
            f"{output_dir}/charts/session_timeline.html",
            f"{output_dir}/charts/session_timeline.png",
            disable_interactive,
        )

    return artifacts
