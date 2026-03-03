import random
from collections import Counter, OrderedDict, defaultdict
from typing import Dict

import pandas as pd

from .base import BaseAggregator
from .stats import hist_median, logger


class DialogAggregator(BaseAggregator):
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
            {"from": a, "prev_from": b, "median_gap": hist_median(hist)}
            for (a, b), hist in self.reply_time_hist.items()
            if hist
        ]
        pair_df = pd.DataFrame(pair_rows) if pair_rows else pd.DataFrame()

        hour_rows = [
            {"hour": h, "from": a, "median_gap": hist_median(hist)}
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
