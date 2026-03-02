# === Standard library ===
import logging
import re
from collections import Counter
from typing import Dict, List, Optional, Set

# === Data handling ===
import pandas as pd

# === Visualization ===
import matplotlib.pyplot as plt
from wordcloud import WordCloud

import emoji
import nltk
from nltk.corpus import stopwords
from pymorphy3 import MorphAnalyzer

from chat_analyzer.utils import finalize_plot, require_non_empty_df

logger = logging.getLogger(__name__)

_URL_RE = re.compile(r"http\S+|www\S+|https\S+", flags=re.MULTILINE)
_EMAIL_RE = re.compile(r"\S+@\S+")
_TOKEN_RE = re.compile(r"[a-zA-Zа-яА-ЯёЁ]+", flags=re.UNICODE)
_FALLBACK_STOP_WORDS = {
    "и", "в", "во", "не", "что", "он", "на", "я", "с", "со", "как", "а", "то", "все", "она",
    "this", "that", "with", "for", "the", "and", "you", "your", "was", "are", "from", "have",
}

_MORPH = MorphAnalyzer()
_LEMMA_CACHE: Dict[str, str] = {}


def _load_stop_words() -> Set[str]:
    words: Set[str] = set()
    for lang in ("russian", "english"):
        try:
            words.update(stopwords.words(lang))
        except LookupError:
            try:
                nltk.download("stopwords", quiet=True)
                words.update(stopwords.words(lang))
            except Exception:
                logger.warning("Не удалось загрузить NLTK stopwords (%s), используется fallback.", lang)
    if not words:
        words = set(_FALLBACK_STOP_WORDS)
    return words


STOP_WORDS = _load_stop_words()


def _base_nlp_df(df: pd.DataFrame, include_forwarded: bool) -> pd.DataFrame:
    required = ["text"]
    if not include_forwarded:
        required.append("is_forwarded")
    if not require_non_empty_df(df, logger, "nlp", required):
        return pd.DataFrame()
    if include_forwarded:
        return df
    return df.loc[~df["is_forwarded"]]


def _lemma(word: str) -> str:
    cached = _LEMMA_CACHE.get(word)
    if cached is not None:
        return cached
    parsed = _MORPH.parse(word)
    normal = parsed[0].normal_form if parsed else word
    _LEMMA_CACHE[word] = normal
    return normal


def preprocess_text_for_nlp(text: str) -> List[str]:
    text = _URL_RE.sub(" ", str(text).lower())
    text = _EMAIL_RE.sub(" ", text)
    tokens = _TOKEN_RE.findall(text)
    processed: List[str] = []
    for token in tokens:
        if len(token) < 3:
            continue
        lemma = _lemma(token)
        if lemma and lemma not in STOP_WORDS and len(lemma) >= 3:
            processed.append(lemma)
    return processed


def _collect_words(df: pd.DataFrame) -> List[str]:
    words: List[str] = []
    total_messages = len(df["text"])
    for idx, text in enumerate(df["text"].dropna(), start=1):
        words.extend(preprocess_text_for_nlp(text))
        if idx % 2000 == 0:
            logger.info("NLP обработано %s/%s сообщений...", idx, total_messages)
    return words


def analyze_keywords(
        df: pd.DataFrame,
        top_n: int = 50,
        save_path: Optional[str] = None,
        include_forwarded: bool = False
) -> None:
    df_nlp = _base_nlp_df(df, include_forwarded=include_forwarded)
    if df_nlp.empty:
        logger.warning("Нет данных для анализа ключевых слов.")
        return

    try:
        all_words = _collect_words(df_nlp)
        if not all_words:
            logger.warning("Не найдено слов для анализа после предобработки.")
            return

        common_words = Counter(all_words).most_common(top_n)
        if not common_words:
            logger.warning("Список самых частых слов пуст.")
            return

        summary = "\n".join([f"- {word}: {count}" for word, count in common_words])
        logger.info("\n--- Анализ ключевых слов ---\nТоп-%s слов:\n%s\n%s", len(common_words), summary, "-" * 20)

        top_words_series = pd.Series(dict(common_words))
        plt.figure(figsize=(12, max(6, top_n // 4)))
        top_words_series.sort_values(ascending=True).plot(kind="barh", color="teal")
        plt.title(f"Топ-{len(common_words)} наиболее частых слов", fontsize=16)
        plt.xlabel("Частота", fontsize=12)
        plt.ylabel("Слово", fontsize=12)
        plt.grid(True, axis="x", linestyle="--", alpha=0.7)
        plt.tight_layout()
        finalize_plot(logger, save_path, "график ключевых слов")
    except Exception as exc:
        logger.error(f"Ошибка при анализе ключевых слов: {exc}", exc_info=True)
        plt.close()


def generate_word_cloud(
        df: pd.DataFrame,
        max_words: int = 100,
        save_path: Optional[str] = None,
        include_forwarded: bool = False
) -> None:
    df_nlp = _base_nlp_df(df, include_forwarded=include_forwarded)
    if df_nlp.empty:
        logger.warning("Нет данных для генерации облака слов.")
        return

    try:
        all_words = _collect_words(df_nlp)
        word_counts = Counter(all_words)
        if not word_counts:
            logger.warning("Счетчик слов пуст для облака слов.")
            return

        actual_max_words = min(max_words, len(word_counts))
        wordcloud = WordCloud(
            width=1200, height=600, background_color="white", max_words=actual_max_words, colormap="viridis"
        ).generate_from_frequencies(word_counts)

        plt.figure(figsize=(15, 8))
        plt.imshow(wordcloud, interpolation="bilinear")
        plt.axis("off")
        plt.tight_layout(pad=0)
        finalize_plot(logger, save_path, "облако слов")
        logger.info("\n--- Генерация облака слов ---\nСлов в облаке: %s\n%s", actual_max_words, "-" * 20)
    except Exception as exc:
        logger.error(f"Ошибка при генерации облака слов: {exc}", exc_info=True)
        plt.close()


def analyze_vocabulary(
        df: pd.DataFrame,
        save_path: Optional[str] = None,
        include_forwarded: bool = False
) -> None:
    df_nlp = _base_nlp_df(df, include_forwarded=include_forwarded)
    if not require_non_empty_df(df_nlp, logger, "analyze_vocabulary", ["text", "from"]):
        return

    try:
        vocab_stats = {}
        for participant, group in df_nlp.groupby("from"):
            participant_words: List[str] = []
            for text in group["text"].dropna():
                participant_words.extend(preprocess_text_for_nlp(text))
            total_words = len(participant_words)
            unique_words = len(set(participant_words))
            lexical_diversity = unique_words / total_words if total_words else 0
            top_5 = Counter(participant_words).most_common(5)
            vocab_stats[participant] = {
                "total_words": total_words,
                "unique_words": unique_words,
                "lexical_diversity": lexical_diversity,
                "top_5_words": top_5,
            }

        if not vocab_stats:
            logger.warning("Не удалось рассчитать словарный запас.")
            return

        lines = ["\n--- Анализ словарного запаса ---"]
        for participant, stats in vocab_stats.items():
            top_words_str = ", ".join([f"{w} ({c})" for w, c in stats["top_5_words"]]) if stats["top_5_words"] else "N/A"
            lines.append(
                f"\n{participant}:\n"
                f"  Общее количество слов: {stats['total_words']}\n"
                f"  Уникальные слова: {stats['unique_words']}\n"
                f"  Лексическое разнообразие: {stats['lexical_diversity']:.3f}\n"
                f"  Топ-5 слов: {top_words_str}"
            )
        lines.append("-" * 20)
        logger.info("\n".join(lines))

        plot_df = pd.DataFrame({
            "participant": list(vocab_stats.keys()),
            "lexical_diversity": [v["lexical_diversity"] for v in vocab_stats.values()],
            "total_words": [v["total_words"] for v in vocab_stats.values()],
        }).sort_values("lexical_diversity", ascending=False)

        if not plot_df.empty:
            fig, axes = plt.subplots(2, 1, figsize=(12, 10))
            plot_df.plot.bar(x="participant", y="lexical_diversity", ax=axes[0], color="steelblue", legend=False)
            axes[0].set_title("Лексическое разнообразие по участникам")
            axes[0].set_xlabel("Участник")
            axes[0].set_ylabel("TTR")
            axes[0].grid(True, axis="y", linestyle="--", alpha=0.7)

            plot_df.plot.bar(x="participant", y="total_words", ax=axes[1], color="darkseagreen", legend=False)
            axes[1].set_title("Общее количество слов по участникам")
            axes[1].set_xlabel("Участник")
            axes[1].set_ylabel("Количество слов")
            axes[1].grid(True, axis="y", linestyle="--", alpha=0.7)
            plt.tight_layout()
            finalize_plot(logger, save_path, "график словарного запаса")
    except Exception as exc:
        logger.error(f"Ошибка при анализе словарного запаса: {exc}", exc_info=True)
        plt.close()


def _extract_emojis(text: str) -> List[str]:
    return [item["emoji"] for item in emoji.emoji_list(str(text))]


def analyze_emoji_usage(
        df: pd.DataFrame,
        save_path: Optional[str] = None,
        include_forwarded: bool = False
) -> None:
    df_nlp = _base_nlp_df(df, include_forwarded=include_forwarded)
    if not require_non_empty_df(df_nlp, logger, "analyze_emoji_usage", ["text", "from"]):
        return

    try:
        emoji_stats = {}
        total_emojis_found = 0
        for participant, group in df_nlp.groupby("from"):
            participant_emojis = []
            for text in group["text"].dropna():
                participant_emojis.extend(_extract_emojis(text))
            emoji_counts = Counter(participant_emojis)
            total_emojis = sum(emoji_counts.values())
            total_emojis_found += total_emojis
            emoji_stats[participant] = {
                "total_emojis": total_emojis,
                "unique_emojis": len(emoji_counts),
                "top_5_emojis": emoji_counts.most_common(5),
                "emoji_per_message": total_emojis / len(group) if len(group) else 0.0,
            }

        if total_emojis_found == 0:
            logger.info("\n--- Анализ использования эмодзи ---\nЭмодзи в чате не найдены.\n%s", "-" * 20)
            return

        lines = ["\n--- Анализ использования эмодзи ---"]
        for participant, stats in emoji_stats.items():
            top = ", ".join([f"{e} ({c})" for e, c in stats["top_5_emojis"]]) if stats["top_5_emojis"] else "N/A"
            lines.append(
                f"\n{participant}:\n"
                f"  Общее количество эмодзи: {stats['total_emojis']}\n"
                f"  Уникальные эмодзи: {stats['unique_emojis']}\n"
                f"  Эмодзи на сообщение (в среднем): {stats['emoji_per_message']:.3f}\n"
                f"  Топ-5 эмодзи: {top}"
            )
        lines.append("-" * 20)
        logger.info("\n".join(lines))

        participants_list = list(emoji_stats.keys())
        total_counts = [stats["total_emojis"] for stats in emoji_stats.values()]
        unique_counts = [stats["unique_emojis"] for stats in emoji_stats.values()]
        per_message_counts = [stats["emoji_per_message"] for stats in emoji_stats.values()]

        fig, axes = plt.subplots(3, 1, figsize=(12, 14))
        pd.Series(total_counts, index=participants_list).sort_values().plot(kind="barh", ax=axes[0], color="coral")
        axes[0].set_title("Общее количество эмодзи")
        axes[0].grid(True, axis="x", linestyle="--", alpha=0.7)

        pd.Series(unique_counts, index=participants_list).sort_values().plot(kind="barh", ax=axes[1], color="goldenrod")
        axes[1].set_title("Количество уникальных эмодзи")
        axes[1].grid(True, axis="x", linestyle="--", alpha=0.7)

        pd.Series(per_message_counts, index=participants_list).sort_values().plot(kind="barh", ax=axes[2], color="slateblue")
        axes[2].set_title("Эмодзи на сообщение")
        axes[2].grid(True, axis="x", linestyle="--", alpha=0.7)

        for ax in axes:
            ax.set_xlabel("Значение")
            ax.set_ylabel("Участник")
        plt.tight_layout()
        finalize_plot(logger, save_path, "график эмодзи")
    except Exception as exc:
        logger.error(f"Ошибка при анализе использования эмодзи: {exc}", exc_info=True)
        plt.close()
