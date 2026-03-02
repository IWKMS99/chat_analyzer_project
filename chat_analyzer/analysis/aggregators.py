# === Standard library ===
import logging
import random
from collections import Counter, defaultdict
from collections import OrderedDict
from dataclasses import dataclass
from typing import Dict

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


def _hist_median(hist: Counter[int]) -> float:
    total = sum(hist.values())
    if total <= 0:
        return 0.0
    threshold = (total + 1) / 2.0
    running = 0
    for value in sorted(hist):
        running += hist[value]
        if running >= threshold:
            return float(value)
    return 0.0


def _hist_quantile(hist: Counter[int], q: float) -> float:
    total = sum(hist.values())
    if total <= 0:
        return 0.0
    target = max(1, int(np.ceil(total * min(max(q, 0.0), 1.0))))
    running = 0
    for value in sorted(hist):
        running += hist[value]
        if running >= target:
            return float(value)
    return float(max(hist))


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
        self.chain_hist = defaultdict(Counter)
        self.chain_sum = Counter()
        self.chain_count = Counter()
        self.chain_max = Counter()
        self._prev_sender = None
        self._prev_date = None
        self._current_chain_len = 0
        self._daily_by_user = Counter()
        self._out_of_order = 0

    def _record_chain(self, sender: str, length: int) -> None:
        if not sender or length <= 0:
            return
        self.chain_hist[sender][int(length)] += 1
        self.chain_sum[sender] += int(length)
        self.chain_count[sender] += 1
        self.chain_max[sender] = max(self.chain_max[sender], int(length))

    def update(self, chunk: pd.DataFrame) -> None:
        if chunk.empty:
            return
        ordered = chunk.sort_values("date")
        for _, row in ordered[["from", "text_length", "date_only", "date"]].iterrows():
            sender = str(row["from"])
            dt = pd.Timestamp(row["date"])
            self.message_counts[sender] += 1
            self.sum_text_len[sender] += int(row["text_length"])
            self._daily_by_user[(str(row["date_only"]), sender)] += 1

            if self._prev_date is not None and dt < self._prev_date:
                self._out_of_order += 1
                if self._out_of_order <= 3 or self._out_of_order % 1000 == 0:
                    logger.warning("Out-of-order message detected in UserAggregator: %s < %s", dt, self._prev_date)
                self._record_chain(self._prev_sender, self._current_chain_len)
                self._prev_sender = sender
                self._current_chain_len = 1
                self._prev_date = dt
                continue

            if self._prev_sender is None:
                self._prev_sender = sender
                self._current_chain_len = 1
            elif self._prev_sender == sender:
                self._current_chain_len += 1
            else:
                self._record_chain(self._prev_sender, self._current_chain_len)
                self._prev_sender = sender
                self._current_chain_len = 1
            self._prev_date = dt

    def finalize(self) -> None:
        if self._prev_sender is not None and self._current_chain_len > 0:
            self._record_chain(self._prev_sender, self._current_chain_len)
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
        for user, ccount in self.chain_count.items():
            if ccount <= 0:
                continue
            hist = self.chain_hist[user]
            chains_rows.append(
                {
                    "from": user,
                    "avg_chain": float(self.chain_sum[user] / ccount),
                    "median_chain": _hist_median(hist),
                    "max_chain": int(self.chain_max[user]),
                    "chains": int(ccount),
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
        self.length_hist = defaultdict(Counter)
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

            self.length_hist[sender][text_len] += 1
            self.total_counts[sender] += 1
            if "?" in text:
                self.question_counts[sender] += 1

            msg_type = "short" if text_len <= self.length_threshold else "long"
            self.short_long_hourly[(hour, sender, msg_type)] += 1

    def result(self) -> Dict[str, pd.DataFrame]:
        length_rows = []
        for sender, hist in self.length_hist.items():
            total = sum(hist.values())
            if total <= 0:
                continue
            mean = sum(length * count for length, count in hist.items()) / total
            length_rows.append(
                {
                    "from": sender,
                    "mean": float(mean),
                    "median": _hist_median(hist),
                    "p95": _hist_quantile(hist, 0.95),
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
        self.response_hist = Counter()
        self.interval_hist = Counter()
        self.response_sum = 0.0
        self.response_count = 0
        self.daily_counts = Counter()
        self.out_of_order_count = 0

    def update(self, chunk: pd.DataFrame) -> None:
        if chunk.empty:
            return

        ordered = chunk.sort_values("date")
        for _, row in ordered[["from", "date", "date_only"]].iterrows():
            sender = str(row["from"])
            dt = pd.Timestamp(row["date"])
            self.daily_counts[str(row["date_only"])] += 1

            if self.prev_date is not None:
                if dt < self.prev_date:
                    self.out_of_order_count += 1
                    if self.out_of_order_count <= 3 or self.out_of_order_count % 1000 == 0:
                        logger.warning("Out-of-order message detected in TemporalAggregator: %s < %s", dt, self.prev_date)
                    self.prev_sender = sender
                    self.prev_date = dt
                    continue

                gap_sec = (dt - self.prev_date).total_seconds()
                if 0 < gap_sec <= self.interval_limit_seconds:
                    self.interval_hist[int(gap_sec)] += 1
                if sender != self.prev_sender:
                    gap_min = gap_sec / 60.0
                    if 0 < gap_min <= self.response_limit_minutes:
                        minute_bin = int(gap_min)
                        self.response_hist[minute_bin] += 1
                        self.response_sum += float(gap_min)
                        self.response_count += 1

            self.prev_sender = sender
            self.prev_date = dt

    def result(self) -> Dict[str, pd.DataFrame | float]:
        daily = pd.Series(self.daily_counts).sort_index()
        daily.index = pd.to_datetime(daily.index)
        avg_response = float(self.response_sum / self.response_count) if self.response_count else 0.0

        response_rows = [{"response_min": minute, "count": count} for minute, count in sorted(self.response_hist.items())]
        interval_rows = [{"interval_sec": sec, "count": count} for sec, count in sorted(self.interval_hist.items())]
        response_df = pd.DataFrame(response_rows) if response_rows else pd.DataFrame()
        interval_df = pd.DataFrame(interval_rows) if interval_rows else pd.DataFrame()
        daily_df = daily.rename("count").to_frame()
        return {
            "avg_response_min": avg_response,
            "response_df": response_df,
            "interval_df": interval_df,
            "daily_df": daily_df,
        }


class DialogAggregator:
    def __init__(
        self,
        response_limit_minutes: float = 240.0,
        session_gap_minutes: float = 30.0,
        max_stored_sessions: int = 20_000,
        max_reply_cache: int = 10_000,
    ):
        self.response_limit_minutes = response_limit_minutes
        self.session_gap_minutes = session_gap_minutes
        self.max_stored_sessions = max_stored_sessions
        self.max_reply_cache = max_reply_cache

        self.prev_sender = None
        self.prev_date = None
        self.reply_edges = Counter()
        self.reply_time_hist = defaultdict(Counter)
        self.hourly_reply_hist = defaultdict(Counter)
        self.message_lookup: OrderedDict[int, tuple[str, pd.Timestamp]] = OrderedDict()

        self._current_session = None
        self._stored_sessions = []
        self._session_seq = 0
        self._rng = random.Random(42)
        self.out_of_order_count = 0

    def _sample_session(self, payload: dict) -> None:
        self._session_seq += 1
        payload_with_id = dict(payload)
        payload_with_id["session_id"] = self._session_seq

        if len(self._stored_sessions) < self.max_stored_sessions:
            self._stored_sessions.append(payload_with_id)
            return

        replace_idx = self._rng.randint(0, self._session_seq - 1)
        if replace_idx < self.max_stored_sessions:
            self._stored_sessions[replace_idx] = payload_with_id

    def _start_session(self, dt: pd.Timestamp, sender: str) -> None:
        self._current_session = {
            "start": dt,
            "end": dt,
            "count": 1,
            "initiator": sender,
        }

    def _close_current_session(self) -> None:
        if self._current_session is None:
            return
        self._sample_session(self._current_session)
        self._current_session = None

    def update(self, chunk: pd.DataFrame) -> None:
        if chunk.empty:
            return

        ordered = chunk.sort_values("date")
        cols = ["from", "date", "hour"]
        has_message_id = "message_id" in ordered.columns
        has_reply_to = "reply_to_message_id" in ordered.columns
        if has_message_id:
            cols.append("message_id")
        if has_reply_to:
            cols.append("reply_to_message_id")

        for _, row in ordered[cols].iterrows():
            sender = str(row["from"])
            dt = pd.Timestamp(row["date"])
            hour = int(row["hour"])
            message_id = row.get("message_id") if has_message_id else None
            reply_to_message_id = row.get("reply_to_message_id") if has_reply_to else None

            if self.prev_date is None:
                self._start_session(dt, sender)
            else:
                if dt < self.prev_date:
                    self.out_of_order_count += 1
                    if self.out_of_order_count <= 3 or self.out_of_order_count % 1000 == 0:
                        logger.warning("Out-of-order message detected in DialogAggregator: %s < %s", dt, self.prev_date)
                    self._close_current_session()
                    self._start_session(dt, sender)
                    self.prev_sender = sender
                    self.prev_date = dt
                    continue

                gap_min = (dt - self.prev_date).total_seconds() / 60.0
                if gap_min > self.session_gap_minutes:
                    self._close_current_session()
                    self._start_session(dt, sender)
                else:
                    self._current_session["end"] = dt
                    self._current_session["count"] += 1

                target_sender = None
                effective_gap_min = gap_min

                reply_to_id = None
                if pd.notna(reply_to_message_id):
                    try:
                        reply_to_id = int(reply_to_message_id)
                    except (TypeError, ValueError):
                        reply_to_id = None

                if reply_to_id is not None:
                    target_info = self.message_lookup.get(reply_to_id)
                    if target_info is not None:
                        target_sender, target_dt = target_info
                        effective_gap_min = (dt - target_dt).total_seconds() / 60.0

                if target_sender is None:
                    # Fallback для экспортов без reply_to_message_id.
                    if sender != self.prev_sender and 0 < gap_min <= self.response_limit_minutes:
                        target_sender = self.prev_sender
                        effective_gap_min = gap_min

                if target_sender is not None and sender != target_sender and effective_gap_min > 0:
                    self.reply_edges[(sender, target_sender)] += 1
                    minute_bin = int(effective_gap_min)
                    self.reply_time_hist[(sender, target_sender)][minute_bin] += 1
                    self.hourly_reply_hist[(hour, sender)][minute_bin] += 1

            self.prev_sender = sender
            self.prev_date = dt

            if pd.notna(message_id):
                try:
                    msg_id = int(message_id)
                    self.message_lookup[msg_id] = (sender, dt)
                    self.message_lookup.move_to_end(msg_id)
                    if len(self.message_lookup) > self.max_reply_cache:
                        self.message_lookup.popitem(last=False)
                except (TypeError, ValueError):
                    pass

    def result(self) -> Dict[str, pd.DataFrame]:
        self._close_current_session()

        edge_rows = [(a, b, c) for (a, b), c in self.reply_edges.items()]
        edges_df = pd.DataFrame(edge_rows, columns=["from", "prev_from", "count"]) if edge_rows else pd.DataFrame()

        pair_rows = [
            {"from": a, "prev_from": b, "median_gap": _hist_median(hist)}
            for (a, b), hist in self.reply_time_hist.items()
            if hist
        ]
        pair_df = pd.DataFrame(pair_rows) if pair_rows else pd.DataFrame()

        hour_rows = [
            {"hour": h, "from": a, "median_gap": _hist_median(hist)}
            for (h, a), hist in self.hourly_reply_hist.items()
            if hist
        ]
        hour_df = pd.DataFrame(hour_rows) if hour_rows else pd.DataFrame()

        sessions_rows = []
        for payload in self._stored_sessions:
            duration = (payload["end"] - payload["start"]).total_seconds() / 60.0
            sessions_rows.append(
                {
                    "session_id": int(payload["session_id"]),
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
        self.reactions_received = Counter()
        self.edited_by_user = Counter()
        self.deleted_by_user = Counter()
        self.total_by_user = Counter()
        self.reply_edges = Counter()
        self.prev_sender = None
        self.prev_date = None
        self.out_of_order_count = 0

    def update(self, chunk: pd.DataFrame) -> None:
        if chunk.empty:
            return
        ordered = chunk.sort_values("date")
        for _, row in ordered[["from", "is_edited", "is_deleted", "reactions", "date"]].iterrows():
            sender = str(row["from"])
            dt = pd.Timestamp(row["date"])

            if self.prev_date is not None and dt < self.prev_date:
                self.out_of_order_count += 1
                if self.out_of_order_count <= 3 or self.out_of_order_count % 1000 == 0:
                    logger.warning("Out-of-order message detected in SocialAggregator: %s < %s", dt, self.prev_date)

            self.total_by_user[sender] += 1
            self.edited_by_user[sender] += int(bool(row["is_edited"]))
            self.deleted_by_user[sender] += int(bool(row["is_deleted"]))

            if self.prev_sender is not None and self.prev_sender != sender:
                self.reply_edges[(sender, self.prev_sender)] += 1

            reactions = row["reactions"] if isinstance(row["reactions"], list) else []
            if reactions:
                # В стандартном Telegram-экспорте неизвестно, кто поставил реакцию.
                # Корректно считаем только реакции, полученные автором сообщения.
                self.reactions_received[sender] += len(reactions)

            self.prev_sender = sender
            self.prev_date = dt

    def result(self) -> Dict[str, pd.DataFrame]:
        reaction_rows = [{"from": user, "count": int(count)} for user, count in self.reactions_received.items()]
        reaction_df = pd.DataFrame(reaction_rows).sort_values("count", ascending=False) if reaction_rows else pd.DataFrame(columns=["from", "count"])
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
