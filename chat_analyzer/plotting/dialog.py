import pandas as pd
import plotly.express as px

from chat_analyzer.plotting.base import PlotArtifact, apply_default_layout, finalize_plotly_figure


def build_dialog_plots(data: dict, output_dir: str, disable_interactive: bool) -> dict[str, PlotArtifact]:
    artifacts: dict[str, PlotArtifact] = {}

    edges = data.get("reply_edges", pd.DataFrame())
    if not edges.empty:
        pivot = edges.pivot(index="from", columns="prev_from", values="count").fillna(0)
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
        pivot = pair.pivot(index="from", columns="prev_from", values="median_gap").fillna(0.0)
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
