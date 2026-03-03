import type { DashboardWidget, DatasetMeta } from "@chat-analyzer/api-contracts";

export interface SummaryKpi {
  key: string;
  label: string;
  value: string;
}

export interface DatasetCardModel {
  id: string;
  title: string;
  moduleLabel: string;
  rows: Array<Record<string, unknown>>;
  columns: string[];
  meta: DatasetMeta | null;
  chartWidget?: DashboardWidget;
}

export interface ChartModel {
  data: Array<Record<string, string | number | null>>;
  xKey: string;
  seriesKeys: string[];
  kind: "line" | "bar";
}
