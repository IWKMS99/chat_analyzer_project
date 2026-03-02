import pandas as pd
import plotly.express as px

from chat_analyzer.plotting.base import PlotArtifact, apply_default_layout, finalize_plotly_figure


def build_nlp_plots(data: dict, output_dir: str, disable_interactive: bool) -> dict[str, PlotArtifact]:
    artifacts: dict[str, PlotArtifact] = {}

    keywords = data.get("keywords", pd.DataFrame())
    if not keywords.empty:
        top_words = keywords.head(40).sort_values("count")
        fig = px.bar(top_words, x="count", y="word", orientation="h")
        apply_default_layout(fig, "Топ ключевых слов", "Частота", "Слово")
        artifacts["keywords"] = finalize_plotly_figure(
            fig,
            "keywords",
            f"{output_dir}/charts/keywords.html",
            f"{output_dir}/charts/keywords.png",
            disable_interactive,
        )

    vocabulary = data.get("vocabulary", pd.DataFrame())
    if not vocabulary.empty:
        fig = px.bar(vocabulary, x="from", y=["lexical_diversity", "total_words"], barmode="group")
        apply_default_layout(fig, "Словарный запас", "Участник", "Значение")
        artifacts["vocabulary"] = finalize_plotly_figure(
            fig,
            "vocabulary",
            f"{output_dir}/charts/vocabulary.html",
            f"{output_dir}/charts/vocabulary.png",
            disable_interactive,
        )

    emoji_df = data.get("emoji", pd.DataFrame())
    if not emoji_df.empty:
        fig = px.bar(emoji_df.head(30), x="emoji", y="count")
        apply_default_layout(fig, "Топ эмодзи", "Эмодзи", "Количество")
        artifacts["emoji"] = finalize_plotly_figure(
            fig,
            "emoji",
            f"{output_dir}/charts/emoji.html",
            f"{output_dir}/charts/emoji.png",
            disable_interactive,
        )

    sent_user = data.get("sentiment_user", pd.DataFrame())
    if not sent_user.empty:
        fig = px.bar(sent_user, x="from", y="sentiment_mean", color="sentiment_mean", color_continuous_scale="RdYlGn")
        apply_default_layout(fig, "Sentiment по участникам", "Участник", "Mean sentiment")
        artifacts["sentiment_user"] = finalize_plotly_figure(
            fig,
            "sentiment_user",
            f"{output_dir}/charts/sentiment_user.html",
            f"{output_dir}/charts/sentiment_user.png",
            disable_interactive,
        )

    sent_day = data.get("sentiment_day", pd.DataFrame())
    if not sent_day.empty:
        fig = px.line(sent_day, x="date_only", y="sentiment_mean", markers=True)
        apply_default_layout(fig, "Sentiment по дням", "Дата", "Mean sentiment")
        artifacts["sentiment_day"] = finalize_plotly_figure(
            fig,
            "sentiment_day",
            f"{output_dir}/charts/sentiment_day.html",
            f"{output_dir}/charts/sentiment_day.png",
            disable_interactive,
        )

    return artifacts
