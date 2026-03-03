from collections import Counter
from typing import Dict

import pandas as pd

from .common import logger


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
