import pandas as pd
import plotly.express as px

from chat_analyzer.plotting.base import PlotArtifact, apply_default_layout, finalize_plotly_figure


def build_user_plots(data: dict, output_dir: str, max_legend: int, disable_interactive: bool) -> dict[str, PlotArtifact]:
    artifacts: dict[str, PlotArtifact] = {}

    counts = data.get("message_counts", pd.Series(dtype=float)).head(max_legend)
    if not counts.empty:
        counts_df = counts.rename_axis("from").reset_index(name="count")
        fig = px.bar(counts_df.sort_values("count"), x="count", y="from", orientation="h")
        apply_default_layout(fig, "Топ пользователей по сообщениям", "Сообщений", "Участник")
        artifacts["user_message_counts"] = finalize_plotly_figure(
            fig,
            "user_message_counts",
            f"{output_dir}/charts/user_message_counts.html",
            f"{output_dir}/charts/user_message_counts.png",
            disable_interactive,
        )

    avg_len = data.get("avg_length", pd.Series(dtype=float)).head(max_legend)
    if not avg_len.empty:
        avg_df = avg_len.rename_axis("from").reset_index(name="avg_length")
        fig = px.bar(avg_df.sort_values("avg_length"), x="avg_length", y="from", orientation="h")
        apply_default_layout(fig, "Средняя длина сообщений", "Символов", "Участник")
        artifacts["user_avg_length"] = finalize_plotly_figure(
            fig,
            "user_avg_length",
            f"{output_dir}/charts/user_avg_length.html",
            f"{output_dir}/charts/user_avg_length.png",
            disable_interactive,
        )

    chains = data.get("chains", pd.DataFrame())
    if not chains.empty:
        fig = px.bar(chains.head(max_legend), x="from", y=["avg_chain", "median_chain", "max_chain"], barmode="group")
        apply_default_layout(fig, "Статистика цепочек сообщений", "Участник", "Длина цепочки")
        artifacts["message_chains"] = finalize_plotly_figure(
            fig,
            "message_chains",
            f"{output_dir}/charts/message_chains.html",
            f"{output_dir}/charts/message_chains.png",
            disable_interactive,
        )

    daily = data.get("daily_by_user", pd.DataFrame())
    if not daily.empty:
        totals = daily.groupby("date_only")["count"].sum().nlargest(5).index
        top_days = daily[daily["date_only"].isin(totals)]
        fig = px.bar(top_days, x="date_only", y="count", color="from")
        apply_default_layout(fig, "Топ активных дней", "Дата", "Сообщений")
        artifacts["most_active_days"] = finalize_plotly_figure(
            fig,
            "most_active_days",
            f"{output_dir}/charts/most_active_days.html",
            f"{output_dir}/charts/most_active_days.png",
            disable_interactive,
        )

    return artifacts
