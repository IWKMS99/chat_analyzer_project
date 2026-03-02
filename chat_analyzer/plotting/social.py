import logging
from pathlib import Path

import pandas as pd
import plotly.express as px

from chat_analyzer.plotting.base import PlotArtifact, apply_default_layout, finalize_plotly_figure

logger = logging.getLogger(__name__)
MAX_SOCIAL_USERS = 50
MAX_SOCIAL_EDGES = 400

try:
    import networkx as nx
except ImportError:  # pragma: no cover
    nx = None

try:
    from pyvis.network import Network
except ImportError:  # pragma: no cover
    Network = None


def _build_graph_html(edges: pd.DataFrame, path: str, max_users: int = MAX_SOCIAL_USERS, max_edges: int = MAX_SOCIAL_EDGES) -> str | None:
    if edges.empty or nx is None or Network is None:
        return None
    clean_edges = edges.dropna(subset=["from", "to", "count"]).copy()
    clean_edges = clean_edges[(clean_edges["from"].astype(str).str.strip() != "") & (clean_edges["to"].astype(str).str.strip() != "")]
    if clean_edges.empty:
        return None
    clean_edges["count"] = pd.to_numeric(clean_edges["count"], errors="coerce").fillna(0.0)
    clean_edges = clean_edges[clean_edges["count"] > 0]
    if clean_edges.empty:
        return None

    influence = (
        clean_edges.groupby("from")["count"].sum().add(clean_edges.groupby("to")["count"].sum(), fill_value=0.0)
        .sort_values(ascending=False)
        .head(max_users)
        .index
    )
    clean_edges = clean_edges[clean_edges["from"].isin(influence) & clean_edges["to"].isin(influence)]
    if clean_edges.empty:
        return None
    clean_edges = clean_edges.sort_values("count", ascending=False).head(max_edges)

    graph = nx.DiGraph()
    for _, row in clean_edges.iterrows():
        graph.add_edge(str(row["from"]), str(row["to"]), weight=float(row["count"]))

    net = Network(height="700px", width="100%", directed=True)
    net.from_nx(graph)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    net.write_html(path)
    return path


def build_social_plots(data: dict, output_dir: str, disable_interactive: bool) -> tuple[dict[str, PlotArtifact], dict[str, str]]:
    artifacts: dict[str, PlotArtifact] = {}
    extra_artifacts: dict[str, str] = {}

    reactions = data.get("reaction_edges", pd.DataFrame())
    if not reactions.empty:
        safe_reactions = reactions.copy()
        safe_reactions["count"] = pd.to_numeric(safe_reactions["count"], errors="coerce").fillna(0)
        safe_reactions = safe_reactions[safe_reactions["count"] > 0]
        top_reactions = safe_reactions.sort_values("count", ascending=False).head(MAX_SOCIAL_USERS)
        if top_reactions.empty:
            top_reactions = safe_reactions.head(0)
        fig = px.bar(top_reactions, x="from", y="count")
        apply_default_layout(fig, "Топ получателей реакций", "Участник", "Реакции")
        artifacts["reaction_received"] = finalize_plotly_figure(
            fig,
            "reaction_received",
            f"{output_dir}/charts/reaction_received.html",
            f"{output_dir}/charts/reaction_received.png",
            disable_interactive,
        )

    ed = data.get("edited_deleted", pd.DataFrame())
    if not ed.empty:
        fig = px.bar(ed, x="from", y=["edited_ratio", "deleted_ratio"], barmode="group")
        apply_default_layout(fig, "Доля edited/deleted сообщений", "Участник", "Доля")
        artifacts["edited_deleted"] = finalize_plotly_figure(
            fig,
            "edited_deleted",
            f"{output_dir}/charts/edited_deleted.html",
            f"{output_dir}/charts/edited_deleted.png",
            disable_interactive,
        )

    reply_edges = data.get("reply_edges", pd.DataFrame())
    graph_path = _build_graph_html(reply_edges, f"{output_dir}/social_graph.html")
    if graph_path:
        extra_artifacts["social_graph"] = graph_path

    return artifacts, extra_artifacts
