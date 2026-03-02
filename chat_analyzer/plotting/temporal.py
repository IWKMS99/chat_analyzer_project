import pandas as pd
import plotly.express as px

from chat_analyzer.plotting.base import PlotArtifact, apply_default_layout, finalize_plotly_figure


def build_temporal_plots(data: dict, output_dir: str, disable_interactive: bool) -> dict[str, PlotArtifact]:
    artifacts: dict[str, PlotArtifact] = {}

    response_df = data.get("response_df", pd.DataFrame())
    if not response_df.empty:
        fig = px.bar(response_df, x="response_min", y="count")
        apply_default_layout(fig, "Распределение времени ответа", "Минуты", "Количество")
        artifacts["response_distribution"] = finalize_plotly_figure(
            fig,
            "response_distribution",
            f"{output_dir}/charts/response_distribution.html",
            f"{output_dir}/charts/response_distribution.png",
            disable_interactive,
        )

    intervals = data.get("interval_df", pd.DataFrame())
    if not intervals.empty:
        fig = px.bar(intervals, x="interval_sec", y="count")
        apply_default_layout(fig, "Интервалы между сообщениями", "Секунды", "Количество")
        artifacts["message_intervals"] = finalize_plotly_figure(
            fig,
            "message_intervals",
            f"{output_dir}/charts/message_intervals.html",
            f"{output_dir}/charts/message_intervals.png",
            disable_interactive,
        )

    daily = data.get("daily_df", pd.DataFrame())
    if not daily.empty:
        daily = daily.copy()
        daily["ma_7"] = daily["count"].rolling(window=7, min_periods=1).mean()
        daily["ma_30"] = daily["count"].rolling(window=30, min_periods=1).mean()
        fig = px.line(daily.reset_index(), x="index", y=["count", "ma_7", "ma_30"])
        apply_default_layout(fig, "Дневная активность и скользящие средние", "Дата", "Сообщений")
        artifacts["daily_activity"] = finalize_plotly_figure(
            fig,
            "daily_activity",
            f"{output_dir}/charts/daily_activity.html",
            f"{output_dir}/charts/daily_activity.png",
            disable_interactive,
        )

    return artifacts
