import pandas as pd
import plotly.express as px

from chat_analyzer.plotting.base import PlotArtifact, apply_default_layout, finalize_plotly_figure


def build_message_plots(data: dict, output_dir: str, max_legend: int, disable_interactive: bool) -> dict[str, PlotArtifact]:
    artifacts: dict[str, PlotArtifact] = {}

    lengths = data.get("lengths", pd.DataFrame())
    if not lengths.empty:
        fig = px.bar(lengths.head(max_legend), x="from", y=["mean", "median", "p95"], barmode="group")
        apply_default_layout(fig, "Длина сообщений", "Участник", "Символов")
        artifacts["message_length"] = finalize_plotly_figure(
            fig,
            "message_length",
            f"{output_dir}/charts/message_length.html",
            f"{output_dir}/charts/message_length.png",
            disable_interactive,
        )

    ratio = data.get("question_ratio", pd.DataFrame())
    if not ratio.empty:
        fig = px.bar(ratio.head(max_legend), x="from", y="ratio")
        apply_default_layout(fig, "Доля вопросов", "Участник", "Доля")
        artifacts["question_ratio"] = finalize_plotly_figure(
            fig,
            "question_ratio",
            f"{output_dir}/charts/question_ratio.html",
            f"{output_dir}/charts/question_ratio.png",
            disable_interactive,
        )

    short_long = data.get("short_long_hourly", pd.DataFrame())
    if not short_long.empty:
        agg = short_long.groupby(["hour", "message_type"], as_index=False)["count"].sum()
        fig = px.line(agg, x="hour", y="count", color="message_type", markers=True)
        apply_default_layout(fig, "Короткие и длинные сообщения по часам", "Час", "Количество")
        artifacts["short_long_hourly"] = finalize_plotly_figure(
            fig,
            "short_long_hourly",
            f"{output_dir}/charts/short_long_hourly.html",
            f"{output_dir}/charts/short_long_hourly.png",
            disable_interactive,
        )

    return artifacts
