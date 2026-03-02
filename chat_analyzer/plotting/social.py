import logging
from pathlib import Path

import pandas as pd
import plotly.express as px

from chat_analyzer.plotting.base import PlotArtifact, apply_default_layout, finalize_plotly_figure

logger = logging.getLogger(__name__)

try:
    import networkx as nx
except ImportError:  # pragma: no cover
    nx = None

try:
    from pyvis.network import Network
except ImportError:  # pragma: no cover
    Network = None


def _build_graph_html(edges: pd.DataFrame, path: str) -> str | None:
    if edges.empty or nx is None or Network is None:
        return None
    clean_edges = edges.dropna(subset=["from", "to", "count"]).copy()
    clean_edges = clean_edges[(clean_edges["from"].astype(str).str.strip() != "") & (clean_edges["to"].astype(str).str.strip() != "")]
    if clean_edges.empty:
        return None

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

    reaction_edges = data.get("reaction_edges", pd.DataFrame())
    if not reaction_edges.empty:
        pivot = reaction_edges.pivot(index="from", columns="to", values="count").fillna(0)
        fig = px.imshow(pivot, text_auto=True, color_continuous_scale="Blues", aspect="auto")
        apply_default_layout(fig, "Кто кому ставит реакции", "Кому", "Кто ставит")
        artifacts["reaction_matrix"] = finalize_plotly_figure(
            fig,
            "reaction_matrix",
            f"{output_dir}/charts/reaction_matrix.html",
            f"{output_dir}/charts/reaction_matrix.png",
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
