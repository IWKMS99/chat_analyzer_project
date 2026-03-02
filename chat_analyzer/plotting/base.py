import logging
import os
from dataclasses import dataclass
from typing import Optional

import plotly.graph_objects as go

logger = logging.getLogger(__name__)


@dataclass
class PlotArtifact:
    name: str
    figure: Optional[go.Figure]
    html_path: Optional[str] = None
    png_path: Optional[str] = None


def apply_default_layout(fig: go.Figure, title: str, x_title: str = "", y_title: str = "") -> go.Figure:
    fig.update_layout(
        title=title,
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(l=40, r=20, t=70, b=40),
        xaxis_title=x_title,
        yaxis_title=y_title,
    )
    return fig


def _ensure_parent(path: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def finalize_plotly_figure(
    fig: go.Figure,
    name: str,
    html_path: Optional[str],
    png_path: Optional[str],
    disable_interactive: bool = False,
) -> PlotArtifact:
    if fig is None:
        return PlotArtifact(name=name, figure=None, html_path=None, png_path=None)

    if html_path and not disable_interactive:
        _ensure_parent(html_path)
        fig.write_html(html_path, include_plotlyjs="cdn", full_html=False)

    saved_png = None
    if png_path:
        _ensure_parent(png_path)
        try:
            fig.write_image(png_path, scale=2)
            saved_png = png_path
        except Exception as exc:
            logger.warning("Не удалось сохранить PNG для %s: %s", name, exc)

    return PlotArtifact(name=name, figure=fig, html_path=html_path if not disable_interactive else None, png_path=saved_png)


def top_columns(df, top_n: int):
    if df is None or df.empty:
        return df
    if df.shape[1] <= top_n:
        return df
    top = df.sum(axis=0).sort_values(ascending=False).head(top_n).index
    return df[top]
