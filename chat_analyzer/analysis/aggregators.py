# === Standard library ===
import logging
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Dict, List, Tuple

# === Third-party ===
import numpy as np
import pandas as pd

from chat_analyzer.analysis.nlp_spacy import default_workers, process_texts_spacy, update_emoji_counter

logger = logging.getLogger(__name__)


@dataclass
class CoreStats:
    total_messages: int
    participants: int
    start: pd.Timestamp | None
    end: pd.Timestamp | None


class SummaryAggregator:
    def __init__(self):
        self.total_messages = 0
        self.participants = set()
        self.start = None
        self.end = None

    def update(self, chunk: pd.DataFrame) -> None:
        if chunk.empty:
            return
        self.total_messages += len(chunk)
        self.participants.update(map(str, chunk["from"].astype(str).unique()))
        cmin = chunk["date"].min()
        cmax = chunk["date"].max()
        self.start = cmin if self.start is None else min(self.start, cmin)
        self.end = cmax if self.end is None else max(self.end, cmax)

    def result(self) -> CoreStats:
        return CoreStats(
            total_messages=self.total_messages,
            participants=len(self.participants),
            start=self.start,
            end=self.end,
        )


class ActivityAggregator:
    def __init__(self):
        self.hourly = Counter()
        self.weekday = Counter()
        self.monthly = Counter()
        self.periods = Counter()

    def update(self, chunk: pd.DataFrame) -> None:
        if chunk.empty:
            return
        for _, row in chunk[["hour", "from", "day_of_week", "date"]].iterrows():
            sender = str(row["from"])
            hour = int(row["hour"])
            day = str(row["day_of_week"])
            month = pd.Timestamp(row["date"]).strftime("%Y-%m")
            self.hourly[(hour, sender)] += 1
            self.weekday[(day, sender)] += 1
            self.monthly[(month, sender)] += 1
            if 5 <= hour < 12:
                period = "morning"
            elif 12 <= hour < 18:
                period = "day"
            elif 18 <= hour < 24:
                period = "evening"
            else:
                period = "night"
            self.periods[(period, sender)] += 1

    def result(self) -> Dict[str, pd.DataFrame]:
        def _pivot(counter, idx, col):
            if not counter:
                return pd.DataFrame()
            df = pd.DataFrame([(k[0], k[1], v) for k, v in counter.items()], columns=[idx, col, "count"])
            return df.pivot(index=idx, columns=col, values="count").fillna(0)

        return {
            "hourly": _pivot(self.hourly, "hour", "from").reindex(range(24), fill_value=0),
            "weekday": _pivot(self.weekday, "day_of_week", "from"),
            "monthly": _pivot(self.monthly, "month", "from"),
            "periods": _pivot(self.periods, "period", "from"),
        }


class UserAggregator:
    def __init__(self):
        self.message_counts = Counter()
        self.sum_text_len = Counter()
        self.chain_lengths = defaultdict(list)
        self._prev_sender = None
        self._current_chain_len = 0
        self._daily_by_user = Counter()

    def update(self, chunk: pd.DataFrame) -> None:
        if chunk.empty:
            return
        ordered = chunk.sort_values("date")
        for _, row in ordered[["from", "text_length", "date_only"]].iterrows():
            sender = str(row["from"])
            self.message_counts[sender] += 1
            self.sum_text_len[sender] += int(row["text_length"])
            self._daily_by_user[(str(row["date_only"]), sender)] += 1

            if self._prev_sender is None:
                self._prev_sender = sender
                self._current_chain_len = 1
            elif self._prev_sender == sender:
                self._current_chain_len += 1
            else:
                self.chain_lengths[self._prev_sender].append(self._current_chain_len)
                self._prev_sender = sender
                self._current_chain_len = 1

    def finalize(self) -> None:
        if self._prev_sender is not None and self._current_chain_len > 0:
            self.chain_lengths[self._prev_sender].append(self._current_chain_len)
            self._current_chain_len = 0

    def result(self) -> Dict[str, pd.DataFrame | Dict[str, float]]:
        self.finalize()
        counts = pd.Series(dict(self.message_counts), name="count").sort_values(ascending=False)
        avg_len = {
            user: (self.sum_text_len[user] / cnt if cnt else 0.0)
            for user, cnt in self.message_counts.items()
        }
        avg_len_series = pd.Series(avg_len, name="avg_text_length").sort_values(ascending=False)

        chains_rows = []
        for user, values in self.chain_lengths.items():
            if not values:
                continue
            arr = np.array(values)
            chains_rows.append(
                {
                    "from": user,
                    "avg_chain": float(arr.mean()),
                    "median_chain": float(np.median(arr)),
                    "max_chain": int(arr.max()),
                    "chains": int(arr.size),
                }
            )
        chains_df = pd.DataFrame(chains_rows).sort_values("chains", ascending=False) if chains_rows else pd.DataFrame()

        day_rows = [(d, u, c) for (d, u), c in self._daily_by_user.items()]
        daily_df = pd.DataFrame(day_rows, columns=["date_only", "from", "count"]) if day_rows else pd.DataFrame()
        return {
            "message_counts": counts,
            "avg_length": avg_len_series,
            "chains": chains_df,
            "daily_by_user": daily_df,
        }


class MessageAggregator:
    def __init__(self, length_threshold: int = 50):
        self.length_threshold = length_threshold
        self.lengths = defaultdict(list)
        self.question_counts = Counter()
        self.total_counts = Counter()
        self.short_long_hourly = Counter()

    def update(self, chunk: pd.DataFrame) -> None:
        if chunk.empty:
            return
        for _, row in chunk[["from", "text_length", "text", "hour"]].iterrows():
            sender = str(row["from"])
            text_len = int(row["text_length"])
            text = str(row["text"])
            hour = int(row["hour"])

            self.lengths[sender].append(text_len)
            self.total_counts[sender] += 1
            if "?" in text:
                self.question_counts[sender] += 1

            msg_type = "short" if text_len <= self.length_threshold else "long"
            self.short_long_hourly[(hour, sender, msg_type)] += 1

    def result(self) -> Dict[str, pd.DataFrame]:
        length_rows = []
        for sender, vals in self.lengths.items():
            arr = np.array(vals)
            length_rows.append(
                {
                    "from": sender,
                    "mean": float(arr.mean()),
                    "median": float(np.median(arr)),
                    "p95": float(np.quantile(arr, 0.95)),
                }
            )
        lengths_df = pd.DataFrame(length_rows) if length_rows else pd.DataFrame()

        ratio_rows = []
        for sender, total in self.total_counts.items():
            q = self.question_counts.get(sender, 0)
            ratio_rows.append({"from": sender, "questions": q, "total": total, "ratio": q / max(total, 1)})
        ratios_df = pd.DataFrame(ratio_rows) if ratio_rows else pd.DataFrame()

        sl_rows = [(h, u, t, c) for (h, u, t), c in self.short_long_hourly.items()]
        sl_df = pd.DataFrame(sl_rows, columns=["hour", "from", "message_type", "count"]) if sl_rows else pd.DataFrame()

        return {"lengths": lengths_df, "question_ratio": ratios_df, "short_long_hourly": sl_df}


class TemporalAggregator:
    def __init__(self, response_limit_minutes: float = 60.0, interval_limit_seconds: float = 3600.0):
        self.response_limit_minutes = response_limit_minutes
        self.interval_limit_seconds = interval_limit_seconds
        self.prev_sender = None
        self.prev_date = None
        self.response_times = []
        self.intervals = []
        self.daily_counts = Counter()

    def update(self, chunk: pd.DataFrame) -> None:
        if chunk.empty:
            return

        ordered = chunk.sort_values("date")
        for _, row in ordered[["from", "date", "date_only"]].iterrows():
            sender = str(row["from"])
            dt = pd.Timestamp(row["date"])
            self.daily_counts[str(row["date_only"])] += 1

            if self.prev_date is not None:
                gap_sec = (dt - self.prev_date).total_seconds()
                if 0 < gap_sec <= self.interval_limit_seconds:
                    self.intervals.append(gap_sec)
                if sender != self.prev_sender:
                    gap_min = gap_sec / 60.0
                    if 0 < gap_min <= self.response_limit_minutes:
                        self.response_times.append(gap_min)

            self.prev_sender = sender
            self.prev_date = dt

    def result(self) -> Dict[str, pd.DataFrame | float]:
        daily = pd.Series(self.daily_counts).sort_index()
        daily.index = pd.to_datetime(daily.index)
        avg_response = float(np.mean(self.response_times)) if self.response_times else 0.0

        response_df = pd.DataFrame({"response_min": self.response_times}) if self.response_times else pd.DataFrame()
        interval_df = pd.DataFrame({"interval_sec": self.intervals}) if self.intervals else pd.DataFrame()
        daily_df = daily.rename("count").to_frame()
        return {
            "avg_response_min": avg_response,
            "response_df": response_df,
            "interval_df": interval_df,
            "daily_df": daily_df,
        }


class DialogAggregator:
    def __init__(self, response_limit_minutes: float = 240.0, session_gap_minutes: float = 30.0):
        self.response_limit_minutes = response_limit_minutes
        self.session_gap_minutes = session_gap_minutes
        self.prev_sender = None
        self.prev_date = None
        self.prev_hour = None
        self.reply_edges = Counter()
        self.reply_times = defaultdict(list)
        self.hourly_reply_times = defaultdict(list)
        self.session_id = 0
        self.sessions = {}

    def update(self, chunk: pd.DataFrame) -> None:
        if chunk.empty:
            return
        ordered = chunk.sort_values("date")
        for _, row in ordered[["from", "date", "hour"]].iterrows():
            sender = str(row["from"])
            dt = pd.Timestamp(row["date"])
            hour = int(row["hour"])

            if self.prev_date is None:
                self.session_id += 1
                self.sessions[self.session_id] = {
                    "start": dt,
                    "end": dt,
                    "count": 1,
                    "initiator": sender,
                }
            else:
                gap_min = (dt - self.prev_date).total_seconds() / 60.0
                if gap_min > self.session_gap_minutes:
                    self.session_id += 1
                    self.sessions[self.session_id] = {
                        "start": dt,
                        "end": dt,
                        "count": 1,
                        "initiator": sender,
                    }
                else:
                    self.sessions[self.session_id]["end"] = dt
                    self.sessions[self.session_id]["count"] += 1

                if sender != self.prev_sender and 0 < gap_min <= self.response_limit_minutes:
                    self.reply_edges[(sender, self.prev_sender)] += 1
                    self.reply_times[(sender, self.prev_sender)].append(gap_min)
                    self.hourly_reply_times[(hour, sender)].append(gap_min)

            self.prev_sender = sender
            self.prev_date = dt
            self.prev_hour = hour

    def result(self) -> Dict[str, pd.DataFrame]:
        edge_rows = [(a, b, c) for (a, b), c in self.reply_edges.items()]
        edges_df = pd.DataFrame(edge_rows, columns=["from", "prev_from", "count"]) if edge_rows else pd.DataFrame()

        pair_rows = [
            {"from": a, "prev_from": b, "median_gap": float(np.median(vals))}
            for (a, b), vals in self.reply_times.items()
            if vals
        ]
        pair_df = pd.DataFrame(pair_rows) if pair_rows else pd.DataFrame()

        hour_rows = [
            {"hour": h, "from": a, "median_gap": float(np.median(vals))}
            for (h, a), vals in self.hourly_reply_times.items()
            if vals
        ]
        hour_df = pd.DataFrame(hour_rows) if hour_rows else pd.DataFrame()

        sessions_rows = []
        for sid, payload in self.sessions.items():
            duration = (payload["end"] - payload["start"]).total_seconds() / 60.0
            sessions_rows.append(
                {
                    "session_id": sid,
                    "start_time": payload["start"],
                    "end_time": payload["end"],
                    "duration_min": duration,
                    "message_count": payload["count"],
                    "initiator": payload["initiator"],
                }
            )
        sessions_df = pd.DataFrame(sessions_rows).sort_values("start_time") if sessions_rows else pd.DataFrame()

        return {
            "reply_edges": edges_df,
            "pair_median": pair_df,
            "hour_median": hour_df,
            "sessions": sessions_df,
        }


class NlpAggregator:
    def __init__(self, include_forwarded: bool = False, max_workers: int | None = None):
        self.include_forwarded = include_forwarded
        self.max_workers = max_workers if max_workers is not None else default_workers()
        self.word_counts = Counter()
        self.user_word_counts = defaultdict(Counter)
        self.emoji_counts = Counter()
        self.sentiment_by_user = defaultdict(list)
        self.sentiment_by_day = defaultdict(list)

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
            self.sentiment_by_user[sender].append(score)
            self.sentiment_by_day[date_only].append(score)

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

        user_sent_rows = [
            {"from": sender, "sentiment_mean": float(np.mean(vals)), "messages": len(vals)}
            for sender, vals in self.sentiment_by_user.items()
            if vals
        ]
        user_sent_df = pd.DataFrame(user_sent_rows).sort_values("sentiment_mean", ascending=False) if user_sent_rows else pd.DataFrame()

        day_sent_rows = [
            {"date_only": day, "sentiment_mean": float(np.mean(vals)), "messages": len(vals)}
            for day, vals in self.sentiment_by_day.items()
            if vals
        ]
        day_sent_df = pd.DataFrame(day_sent_rows).sort_values("date_only") if day_sent_rows else pd.DataFrame()

        return {
            "keywords": keywords,
            "vocabulary": vocab_df,
            "emoji": emoji_df,
            "sentiment_user": user_sent_df,
            "sentiment_day": day_sent_df,
        }


class AnomalyAggregator:
    def __init__(self, threshold: float = 2.0, mode: str = "robust"):
        self.threshold = threshold
        self.mode = mode
        self.daily_counts = Counter()

    def update(self, chunk: pd.DataFrame) -> None:
        if chunk.empty:
            return
        day_counts = chunk.groupby("date_only").size()
        for day, count in day_counts.items():
            self.daily_counts[str(day)] += int(count)

    def result(self) -> Dict[str, pd.DataFrame | Dict[str, float | int | str]]:
        if not self.daily_counts:
            return {"daily": pd.DataFrame(), "anomalies": pd.DataFrame(), "metrics": {"mode": self.mode, "threshold": self.threshold}}

        daily = pd.Series(self.daily_counts).sort_index().astype(float)
        daily.index = pd.to_datetime(daily.index)
        df = daily.rename("count").to_frame()
        values = df["count"].values

        robust_score = np.zeros_like(values)
        median = float(np.median(values))
        mad = float(np.median(np.abs(values - median)))
        if mad > 0:
            robust_score = 0.6745 * (values - median) / mad

        zscore = np.zeros_like(values)
        std = float(np.std(values))
        mean = float(np.mean(values))
        if std > 0:
            zscore = (values - mean) / std

        out = df.copy()
        out["robust_score"] = robust_score
        out["zscore"] = zscore

        if self.mode == "robust":
            anomalies = out[np.abs(out["robust_score"]) >= self.threshold]
        elif self.mode == "zscore":
            anomalies = out[np.abs(out["zscore"]) >= self.threshold]
        else:
            anomalies = out[(np.abs(out["robust_score"]) >= self.threshold) | (np.abs(out["zscore"]) >= self.threshold)]

        metrics = {
            "mode": self.mode,
            "threshold": self.threshold,
            "robust_count": int((np.abs(out["robust_score"]) >= self.threshold).sum()),
            "zscore_count": int((np.abs(out["zscore"]) >= self.threshold).sum()),
        }
        return {"daily": out, "anomalies": anomalies, "metrics": metrics}


class SocialAggregator:
    def __init__(self):
        self.reaction_edges = Counter()
        self.edited_by_user = Counter()
        self.deleted_by_user = Counter()
        self.total_by_user = Counter()
        self.reply_edges = Counter()
        self.prev_sender = None

    def update(self, chunk: pd.DataFrame) -> None:
        if chunk.empty:
            return
        ordered = chunk.sort_values("date")
        for _, row in ordered[["from", "is_edited", "is_deleted", "reactions"]].iterrows():
            sender = str(row["from"])
            self.total_by_user[sender] += 1
            self.edited_by_user[sender] += int(bool(row["is_edited"]))
            self.deleted_by_user[sender] += int(bool(row["is_deleted"]))

            if self.prev_sender is not None and self.prev_sender != sender:
                self.reply_edges[(sender, self.prev_sender)] += 1

            reactions = row["reactions"] if isinstance(row["reactions"], list) else []
            if self.prev_sender is not None and reactions:
                self.reaction_edges[(sender, self.prev_sender)] += len(reactions)

            self.prev_sender = sender

    def result(self) -> Dict[str, pd.DataFrame]:
        reaction_rows = [(a, b, c) for (a, b), c in self.reaction_edges.items()]
        reaction_df = (
            pd.DataFrame(reaction_rows, columns=["from", "to", "count"])
            if reaction_rows
            else pd.DataFrame(columns=["from", "to", "count"])
        )
        reply_rows = [(a, b, c) for (a, b), c in self.reply_edges.items()]
        reply_df = (
            pd.DataFrame(reply_rows, columns=["from", "to", "count"])
            if reply_rows
            else pd.DataFrame(columns=["from", "to", "count"])
        )

        edited_rows = []
        for user, total in self.total_by_user.items():
            edited = self.edited_by_user.get(user, 0)
            deleted = self.deleted_by_user.get(user, 0)
            edited_rows.append(
                {
                    "from": user,
                    "total": total,
                    "edited": edited,
                    "deleted": deleted,
                    "edited_ratio": edited / max(total, 1),
                    "deleted_ratio": deleted / max(total, 1),
                }
            )
        edited_df = (
            pd.DataFrame(edited_rows).sort_values("total", ascending=False)
            if edited_rows
            else pd.DataFrame(columns=["from", "total", "edited", "deleted", "edited_ratio", "deleted_ratio"])
        )
        return {
            "reaction_edges": reaction_df,
            "reply_edges": reply_df,
            "edited_deleted": edited_df,
        }
