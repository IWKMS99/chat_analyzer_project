import pandas as pd
import plotly.express as px

from chat_analyzer.plotting.base import PlotArtifact, apply_default_layout, finalize_plotly_figure


def build_anomaly_plots(data: dict, output_dir: str, disable_interactive: bool) -> dict[str, PlotArtifact]:
    artifacts: dict[str, PlotArtifact] = {}

    daily = data.get("daily", pd.DataFrame())
    if daily is not None and not daily.empty:
        daily = daily.reset_index().rename(columns={"index": "date"})
        fig = px.line(daily, x="date", y=["count"], markers=True)
        apply_default_layout(fig, "Активность по дням", "Дата", "Сообщений")
        artifacts["daily_count"] = finalize_plotly_figure(
            fig,
            "daily_count",
            f"{output_dir}/charts/daily_count.html",
            f"{output_dir}/charts/daily_count.png",
            disable_interactive,
        )

    anomalies = data.get("anomalies", pd.DataFrame())
    if anomalies is not None and not anomalies.empty:
        an = anomalies.reset_index().rename(columns={"index": "date"})
        fig = px.bar(an, x="date", y="count", color="count")
        apply_default_layout(fig, "Аномальные дни", "Дата", "Сообщений")
        artifacts["anomalies"] = finalize_plotly_figure(
            fig,
            "anomalies",
            f"{output_dir}/charts/anomalies.html",
            f"{output_dir}/charts/anomalies.png",
            disable_interactive,
        )

    return artifacts
