export type AnalysisStatus = "queued" | "running" | "done" | "failed";
export type AnalysisPhase = "parsing" | "analyzing" | "serializing" | "storing" | "done" | "failed";

export interface AnalysisCreatedResponse {
  analysis_id: string;
  status: AnalysisStatus;
  created_at: string;
}

export interface AnalysisStatusResponse {
  analysis_id: string;
  status: AnalysisStatus;
  phase: AnalysisPhase;
  progress_pct: number;
  eta_sec: number | null;
  warnings: string[];
  error_code: string | null;
  error_message: string | null;
}

export interface AnalysisListItem {
  analysis_id: string;
  status: AnalysisStatus;
  phase: AnalysisPhase;
  progress_pct: number;
  created_at: string;
  updated_at: string;
}

export interface AnalysisListResponse {
  items: AnalysisListItem[];
}

export type DashboardLayout = "single" | "two-column" | "masonry";

export interface DashboardTab {
  id: string;
  title: string;
  order: number;
  layout: DashboardLayout;
  default_open_sections: string[];
}

export type ColumnKind = "temporal" | "quantitative" | "ordinal" | "nominal" | "unknown";

export interface DashboardColumnMeta {
  name: string;
  kind: ColumnKind;
}

export interface DatasetMeta {
  row_count: number;
  columns: DashboardColumnMeta[];
  semantic_kind: string;
  recommended_widget: "chart" | "table" | "both";
}

export interface ChartConfig {
  kind: "line" | "bar" | "area" | "scatter" | "histogram";
  x: string;
  y: string;
  series: string | null;
  aggregation: string | null;
  formatters: Record<string, string>;
}

export interface TableConfig {
  columns: string[];
  default_limit: number;
  sortable: boolean;
  format: Record<string, string>;
}

interface DashboardWidgetBase {
  id: string;
  tab_id: string;
  title: string;
  priority: number;
  section: string;
  collapsed_by_default: boolean;
  empty_state: string | null;
  severity?: "info" | "warning" | "error" | null;
  format?: string | null;
}

export interface ChartWidget extends DashboardWidgetBase {
  type: "chart";
  dataset: string;
  vega_lite_spec: Record<string, unknown>;
  chart_config: ChartConfig;
}

export interface TableWidget extends DashboardWidgetBase {
  type: "table";
  dataset: string;
  table_config: TableConfig;
}

export interface KpiWidget extends DashboardWidgetBase {
  type: "kpi";
  value: string | number | null;
}

export interface TextWidget extends DashboardWidgetBase {
  type: "text";
  text: string | null;
}

export type DashboardWidget = ChartWidget | TableWidget | KpiWidget | TextWidget;

export interface DashboardResponse {
  schema_version: "2.1";
  analysis_id: string;
  summary: Record<string, unknown>;
  tabs: DashboardTab[];
  widgets: DashboardWidget[];
  datasets: Record<string, Array<Record<string, unknown>>>;
  dataset_meta: Record<string, DatasetMeta>;
  metadata: Record<string, unknown>;
}
