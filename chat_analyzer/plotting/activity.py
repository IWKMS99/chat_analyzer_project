import pandas as pd
import plotly.express as px

from chat_analyzer.plotting.base import PlotArtifact, apply_default_layout, finalize_plotly_figure, top_columns


def build_activity_plots(data: dict, output_dir: str, max_legend: int, disable_interactive: bool) -> dict[str, PlotArtifact]:
    artifacts: dict[str, PlotArtifact] = {}

    hourly = top_columns(data.get("hourly", pd.DataFrame()), max_legend)
    if not hourly.empty:
        fig = px.line(hourly.reset_index(), x="hour", y=hourly.columns, markers=True)
        apply_default_layout(fig, "Активность по часам", "Час", "Сообщений")
        artifacts["activity_hourly"] = finalize_plotly_figure(
            fig,
            "activity_hourly",
            f"{output_dir}/charts/activity_hourly.html",
            f"{output_dir}/charts/activity_hourly.png",
            disable_interactive,
        )

    weekday = top_columns(data.get("weekday", pd.DataFrame()), max_legend)
    if not weekday.empty:
        weekday = weekday.reindex(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]).fillna(0)
        fig = px.bar(weekday.reset_index(), x="day_of_week", y=weekday.columns, barmode="stack")
        apply_default_layout(fig, "Активность по дням недели", "День", "Сообщений")
        artifacts["activity_weekday"] = finalize_plotly_figure(
            fig,
            "activity_weekday",
            f"{output_dir}/charts/activity_weekday.html",
            f"{output_dir}/charts/activity_weekday.png",
            disable_interactive,
        )

    monthly = top_columns(data.get("monthly", pd.DataFrame()), max_legend)
    if not monthly.empty:
        fig = px.line(monthly.reset_index(), x="month", y=monthly.columns, markers=True)
        apply_default_layout(fig, "Активность по месяцам", "Месяц", "Сообщений")
        artifacts["activity_monthly"] = finalize_plotly_figure(
            fig,
            "activity_monthly",
            f"{output_dir}/charts/activity_monthly.html",
            f"{output_dir}/charts/activity_monthly.png",
            disable_interactive,
        )

    periods = top_columns(data.get("periods", pd.DataFrame()), max_legend)
    if not periods.empty:
        fig = px.bar(periods.reset_index(), x="period", y=periods.columns, barmode="group")
        apply_default_layout(fig, "Распределение по периодам суток", "Период", "Сообщений")
        artifacts["activity_periods"] = finalize_plotly_figure(
            fig,
            "activity_periods",
            f"{output_dir}/charts/activity_periods.html",
            f"{output_dir}/charts/activity_periods.png",
            disable_interactive,
        )

    return artifacts
