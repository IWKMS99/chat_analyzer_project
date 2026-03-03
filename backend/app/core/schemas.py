from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class AnalysisCreatedResponse(BaseModel):
    analysis_id: str
    status: str
    created_at: datetime


class AnalysisStatusResponse(BaseModel):
    analysis_id: str
    status: Literal["queued", "running", "done", "failed"]
    phase: Literal["parsing", "analyzing", "serializing", "storing", "done", "failed"]
    progress_pct: int = Field(ge=0, le=100)
    eta_sec: int | None = None
    warnings: list[str] = Field(default_factory=list)
    error_code: str | None = None
    error_message: str | None = None


class AnalysisListItem(BaseModel):
    analysis_id: str
    status: str
    phase: str
    progress_pct: int = Field(ge=0, le=100)
    created_at: datetime
    updated_at: datetime


class AnalysisListResponse(BaseModel):
    items: list[AnalysisListItem] = Field(default_factory=list)


class DashboardTab(BaseModel):
    id: str
    title: str
    order: int = Field(ge=0)
    layout: Literal["single", "two-column", "masonry"] = "two-column"
    default_open_sections: list[str] = Field(default_factory=lambda: ["highlights", "charts"])


class DashboardColumnMeta(BaseModel):
    name: str
    kind: Literal["temporal", "quantitative", "ordinal", "nominal", "unknown"]


class DatasetMeta(BaseModel):
    row_count: int = Field(ge=0)
    columns: list[DashboardColumnMeta] = Field(default_factory=list)
    semantic_kind: str = "table"
    recommended_widget: Literal["chart", "table", "both"] = "both"


class ChartConfig(BaseModel):
    kind: Literal["line", "bar", "area", "scatter", "histogram"]
    x: str
    y: str
    series: str | None = None
    aggregation: str | None = None
    formatters: dict[str, str] = Field(default_factory=dict)


class TableConfig(BaseModel):
    columns: list[str] = Field(default_factory=list)
    default_limit: int = Field(default=25, ge=1, le=500)
    sortable: bool = True
    format: dict[str, str] = Field(default_factory=dict)


class DashboardWidget(BaseModel):
    id: str
    tab_id: str
    type: Literal["chart", "table", "kpi", "text"]
    title: str
    priority: int = Field(default=100, ge=0)
    section: str = "main"
    collapsed_by_default: bool = False
    dataset: str | None = None
    vega_lite_spec: dict[str, Any] | None = None
    chart_config: ChartConfig | None = None
    table_config: TableConfig | None = None
    value: str | int | float | None = None
    text: str | None = None
    severity: Literal["info", "warning", "error"] | None = None
    format: str | None = None
    empty_state: str | None = None


class DashboardResponse(BaseModel):
    schema_version: Literal["2.1"] = "2.1"
    analysis_id: str
    summary: dict[str, Any]
    tabs: list[DashboardTab]
    widgets: list[DashboardWidget]
    datasets: dict[str, list[dict[str, Any]]]
    dataset_meta: dict[str, DatasetMeta] = Field(default_factory=dict)
    metadata: dict[str, Any]


class HealthResponse(BaseModel):
    status: str
    sqlite_ok: bool
    storage_ok: bool
