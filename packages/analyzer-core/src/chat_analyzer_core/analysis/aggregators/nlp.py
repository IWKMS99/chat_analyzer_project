from collections import Counter, defaultdict
from typing import Dict

import pandas as pd

from chat_analyzer_core.analysis.nlp_spacy import default_workers, process_texts_spacy, update_emoji_counter


class NlpAggregator:
    def __init__(self, include_forwarded: bool = False, max_workers: int | None = None):
        self.include_forwarded = include_forwarded
        self.max_workers = max_workers if max_workers is not None else default_workers()
        self.word_counts = Counter()
        self.user_word_counts = defaultdict(Counter)
        self.emoji_counts = Counter()
        self.sentiment_user_sum = Counter()
        self.sentiment_user_count = Counter()
        self.sentiment_day_sum = Counter()
        self.sentiment_day_count = Counter()

    def update(self, chunk: pd.DataFrame) -> None:
        if chunk.empty:
            return

        c = chunk
        if not self.include_forwarded and "is_forwarded" in c.columns:
            c = c.loc[~c["is_forwarded"]]
        if c.empty:
            return

        texts = c["text"].astype(str).tolist()
        batch = process_texts_spacy(texts=texts, n_process=self.max_workers)
        update_emoji_counter(self.emoji_counts, texts)

        for idx, tokens in enumerate(batch.tokens_per_text):
            sender = str(c.iloc[idx]["from"])
            date_only = str(c.iloc[idx]["date_only"])
            self.word_counts.update(tokens)
            self.user_word_counts[sender].update(tokens)
            score = float(batch.sentiment_scores[idx])
            self.sentiment_user_sum[sender] += score
            self.sentiment_user_count[sender] += 1
            self.sentiment_day_sum[date_only] += score
            self.sentiment_day_count[date_only] += 1

    def result(self) -> Dict[str, pd.DataFrame]:
        keywords = pd.DataFrame(self.word_counts.most_common(200), columns=["word", "count"])

        vocab_rows = []
        for sender, wc in self.user_word_counts.items():
            total_words = sum(wc.values())
            unique_words = len(wc)
            vocab_rows.append(
                {
                    "from": sender,
                    "total_words": total_words,
                    "unique_words": unique_words,
                    "lexical_diversity": (unique_words / total_words) if total_words else 0.0,
                }
            )
        vocab_df = pd.DataFrame(vocab_rows).sort_values("lexical_diversity", ascending=False) if vocab_rows else pd.DataFrame()

        emoji_df = pd.DataFrame(self.emoji_counts.most_common(100), columns=["emoji", "count"])

        user_sent_rows = []
        for sender, cnt in self.sentiment_user_count.items():
            if cnt <= 0:
                continue
            user_sent_rows.append(
                {
                    "from": sender,
                    "sentiment_mean": float(self.sentiment_user_sum[sender] / cnt),
                    "messages": int(cnt),
                }
            )
        user_sent_df = pd.DataFrame(user_sent_rows).sort_values("sentiment_mean", ascending=False) if user_sent_rows else pd.DataFrame()

        day_sent_rows = []
        for day, cnt in self.sentiment_day_count.items():
            if cnt <= 0:
                continue
            day_sent_rows.append(
                {
                    "date_only": day,
                    "sentiment_mean": float(self.sentiment_day_sum[day] / cnt),
                    "messages": int(cnt),
                }
            )
        day_sent_df = pd.DataFrame(day_sent_rows).sort_values("date_only") if day_sent_rows else pd.DataFrame()

        return {
            "keywords": keywords,
            "vocabulary": vocab_df,
            "emoji": emoji_df,
            "sentiment_user": user_sent_df,
            "sentiment_day": day_sent_df,
        }
