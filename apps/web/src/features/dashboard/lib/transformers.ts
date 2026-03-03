import type { DashboardResponse, DashboardWidget } from "@chat-analyzer/api-contracts";
import type { ChartModel, DatasetCardModel, ModuleKpi, PreviewKpi, SummaryKpi } from "../model";
import { formatMaybeDate, humanize, safeString } from "./formatters";

const DAY_OF_WEEK_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const PERIOD_ORDER = ["night", "morning", "day", "evening"];
const MAX_CHART_SERIES = 8;

type XValue = string | number;

function parseNumeric(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string" && value.trim() !== "") {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }
  return null;
}

function normalizeX(value: unknown): XValue {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string") {
    return value;
  }
  if (typeof value === "boolean") {
    return value ? "true" : "false";
  }
  return "-";
}

function formatMetricValue(value: number): string {
  if (Math.abs(value) >= 1000) {
    return value.toLocaleString(undefined, { maximumFractionDigits: 1 });
  }

  if (Number.isInteger(value)) {
    return value.toLocaleString();
  }

  return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function buildPreviewKpis(rows: Array<Record<string, unknown>>, columns: string[]): PreviewKpi[] {
  if (!rows.length || !columns.length) {
    return [];
  }

  const stats = columns
    .map((column) => {
      let total = 0;
      let count = 0;

      rows.forEach((row) => {
        const numeric = parseNumeric(row[column]);
        if (numeric === null) {
          return;
        }
        total += numeric;
        count += 1;
      });

      if (count === 0) {
        return null;
      }

      return {
        column,
        count,
        average: total / count,
      };
    })
    .filter((item): item is { column: string; count: number; average: number } => item !== null)
    .sort((a, b) => b.count - a.count || a.column.localeCompare(b.column))
    .slice(0, 2);

  return stats.map((item) => ({
    key: item.column,
    label: `Avg ${humanize(item.column)}`,
    value: formatMetricValue(item.average),
  }));
}

function topSeriesByTotal(rows: Array<Record<string, unknown>>, keys: string[]): string[] {
  const totals = new Map<string, number>();
  keys.forEach((key) => totals.set(key, 0));

  rows.forEach((row) => {
    keys.forEach((key) => {
      const numeric = parseNumeric(row[key]);
      if (numeric === null) {
        return;
      }
      totals.set(key, (totals.get(key) ?? 0) + numeric);
    });
  });

  return Array.from(totals.entries())
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .map(([key]) => key);
}

function normalizeRowsFromFold(
  rows: Array<Record<string, unknown>>,
  chartWidget?: DashboardWidget,
): Array<Record<string, unknown>> {
  const transforms = chartWidget?.vega_lite_spec?.transform;
  if (!Array.isArray(transforms) || transforms.length === 0) {
    return rows;
  }

  const foldTransform = transforms.find((item) => item && typeof item === "object" && Array.isArray((item as { fold?: unknown[] }).fold)) as
    | { fold: unknown[]; as?: unknown[] }
    | undefined;
  if (!foldTransform) {
    return rows;
  }

  const foldFields = foldTransform.fold.filter((item): item is string => typeof item === "string" && item.trim() !== "");
  if (!foldFields.length) {
    return rows;
  }

  const xField = chartWidget?.chart_config?.x;
  if (!xField) {
    return rows;
  }

  const asValues = Array.isArray(foldTransform.as) ? foldTransform.as : [];
  const seriesField = typeof asValues[0] === "string" && asValues[0].trim() !== "" ? asValues[0] : "series";
  const valueField = typeof asValues[1] === "string" && asValues[1].trim() !== "" ? asValues[1] : "value";

  const longRows: Array<Record<string, unknown>> = [];
  rows.forEach((row) => {
    if (!(xField in row)) {
      return;
    }
    const xValue = row[xField];
    foldFields.forEach((column) => {
      const numeric = parseNumeric(row[column]);
      if (numeric === null) {
        return;
      }
      longRows.push({
        [xField]: xValue,
        [seriesField]: column,
        [valueField]: numeric,
      });
    });
  });

  return longRows.length > 0 ? longRows : rows;
}

function xSortValue(xField: string, value: XValue): number | null {
  if (xField === "day_of_week" && typeof value === "string") {
    const rank = DAY_OF_WEEK_ORDER.indexOf(value);
    return rank >= 0 ? rank : null;
  }

  if (xField === "period" && typeof value === "string") {
    const rank = PERIOD_ORDER.indexOf(value);
    return rank >= 0 ? rank : null;
  }

  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }

  if (typeof value !== "string") {
    return null;
  }

  const directNumeric = Number(value);
  if (Number.isFinite(directNumeric) && value.trim() !== "") {
    return directNumeric;
  }

  if (/^\d{4}-\d{2}$/.test(value)) {
    const monthEpoch = Date.parse(`${value}-01T00:00:00Z`);
    return Number.isFinite(monthEpoch) ? monthEpoch : null;
  }

  const dateEpoch = Date.parse(value);
  return Number.isFinite(dateEpoch) ? dateEpoch : null;
}

function sortChartData(data: Array<Record<string, string | number | null>>, xField: string): Array<Record<string, string | number | null>> {
  if (data.length < 2) {
    return data;
  }

  const sortable = data.map((row) => xSortValue(xField, normalizeX(row.x)));
  if (sortable.some((value) => value === null)) {
    return data;
  }

  return [...data]
    .map((row, index) => ({ row, sort: sortable[index] as number, index }))
    .sort((a, b) => a.sort - b.sort || a.index - b.index)
    .map((item) => item.row);
}

export function summaryKpis(dashboard: DashboardResponse): SummaryKpi[] {
  const summary = dashboard.summary ?? {};
  const keys = ["total_messages", "participants", "start", "end", "timezone"] as const;

  return keys.map((key) => {
    const raw = summary[key];
    return {
      key,
      value: key === "start" || key === "end" ? formatMaybeDate(raw) : safeString(raw),
    };
  });
}

export function moduleKpis(dashboard: DashboardResponse): Record<string, ModuleKpi[]> {
  const grouped: Record<string, ModuleKpi[]> = {};

  for (const widget of dashboard.widgets ?? []) {
    if (widget.type !== "kpi" || widget.tab_id === "overview") {
      continue;
    }

    const tabId = widget.tab_id;
    if (!grouped[tabId]) {
      grouped[tabId] = [];
    }

    grouped[tabId].push({
      id: widget.id,
      tabId,
      title: widget.title,
      value: widget.format === "datetime" ? formatMaybeDate(widget.value) : safeString(widget.value),
      format: widget.format ?? undefined,
      severity: widget.severity ?? undefined,
      priority: widget.priority ?? 100,
    });
  }

  Object.keys(grouped).forEach((tabId) => {
    grouped[tabId].sort((a, b) => a.priority - b.priority || a.title.localeCompare(b.title));
  });

  return grouped;
}

export function buildChartModel(rows: Array<Record<string, unknown>>, chartWidget?: DashboardWidget): ChartModel | null {
  if (!rows.length) {
    return null;
  }

  const normalizedRows = normalizeRowsFromFold(rows, chartWidget);
  const first = normalizedRows[0] ?? {};
  const keys = Object.keys(first);
  if (!keys.length) {
    return null;
  }

  const xField =
    chartWidget?.chart_config?.x && keys.includes(chartWidget.chart_config.x)
      ? chartWidget.chart_config.x
      : keys.find((key) => normalizedRows.some((row) => parseNumeric(row[key]) === null)) ?? keys[0];

  const kind = chartWidget?.chart_config?.kind === "bar" || chartWidget?.chart_config?.kind === "histogram" ? "bar" : "line";
  const requestedY = chartWidget?.chart_config?.y;
  const requestedSeries = chartWidget?.chart_config?.series;

  const numericKeys = keys.filter((key) => key !== xField && normalizedRows.some((row) => parseNumeric(row[key]) !== null));

  if (!numericKeys.length) {
    return null;
  }

  const hasLongSeries =
    Boolean(requestedSeries) &&
    normalizedRows.some((row) => row[requestedSeries as string] !== undefined) &&
    Boolean(requestedY) &&
    normalizedRows.some((row) => parseNumeric(row[requestedY as string]) !== null);

  if (hasLongSeries) {
    const bucket = new Map<string, Record<string, string | number | null>>();
    const seriesTotals = new Map<string, number>();

    normalizedRows.forEach((row) => {
      const xValue = normalizeX(row[xField]);
      const xKey = `${typeof xValue}:${xValue}`;
      const seriesValue = safeString(row[requestedSeries as string]);
      const yValue = parseNumeric(row[requestedY as string]);
      if (yValue === null) {
        return;
      }

      if (!bucket.has(xKey)) {
        bucket.set(xKey, { x: xValue });
      }

      const currentRow = bucket.get(xKey)!;
      const previousValue = currentRow[seriesValue];
      currentRow[seriesValue] = typeof previousValue === "number" ? previousValue + yValue : yValue;
      seriesTotals.set(seriesValue, (seriesTotals.get(seriesValue) ?? 0) + yValue);
    });

    const seriesKeys = Array.from(seriesTotals.entries())
      .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
      .slice(0, MAX_CHART_SERIES)
      .map(([key]) => key);

    if (!seriesKeys.length) {
      return null;
    }

    const data = Array.from(bucket.values()).map((row) => {
      const compact: Record<string, string | number | null> = { x: row.x ?? "-" };
      seriesKeys.forEach((key) => {
        compact[key] = row[key] ?? null;
      });
      return compact;
    });

    return {
      data: sortChartData(data, xField),
      xKey: "x",
      seriesKeys,
      kind,
    };
  }

  const rankedNumericKeys = topSeriesByTotal(normalizedRows, numericKeys);
  const seriesKeys =
    requestedY && rankedNumericKeys.includes(requestedY)
      ? [requestedY]
      : requestedY && !rankedNumericKeys.includes(requestedY)
        ? rankedNumericKeys.slice(0, MAX_CHART_SERIES)
        : rankedNumericKeys.slice(0, MAX_CHART_SERIES);

  const data = normalizedRows.map((row) => {
    const record: Record<string, string | number | null> = { x: normalizeX(row[xField]) };
    seriesKeys.forEach((key) => {
      record[key] = parseNumeric(row[key]);
    });
    return record;
  });

  return {
    data: sortChartData(data, xField),
    xKey: "x",
    seriesKeys,
    kind,
  };
}

export function buildDatasetCards(dashboard: DashboardResponse): DatasetCardModel[] {
  const tabTitleById = new Map<string, string>();
  (dashboard.tabs ?? []).forEach((tab) => {
    tabTitleById.set(tab.id, tab.title);
  });

  const fallbackTabId = dashboard.tabs?.[0]?.id ?? "all";

  const datasetWidgetMeta = new Map<
    string,
    {
      tabId: string;
      tabTitle: string;
      priority: number;
      chartWidget?: DashboardWidget;
      title?: string;
    }
  >();

  for (const widget of dashboard.widgets ?? []) {
    if (!widget.dataset) {
      continue;
    }

    const current = datasetWidgetMeta.get(widget.dataset);
    const nextPriority = widget.priority ?? 100;
    const tabTitle = tabTitleById.get(widget.tab_id) ?? humanize(widget.tab_id);

    if (!current) {
      datasetWidgetMeta.set(widget.dataset, {
        tabId: widget.tab_id,
        tabTitle,
        priority: nextPriority,
        chartWidget: widget.type === "chart" ? widget : undefined,
        title: widget.title,
      });
      continue;
    }

    if (nextPriority < current.priority) {
      current.priority = nextPriority;
    }
    if (widget.type === "chart") {
      current.chartWidget = widget;
    }
    if (!current.title && widget.title) {
      current.title = widget.title;
    }
  }

  const entries = Object.entries(dashboard.datasets ?? {});
  return entries
    .map(([datasetId, rows]) => {
      const normalizedRows = Array.isArray(rows)
        ? rows.filter((item): item is Record<string, unknown> => !!item && typeof item === "object" && !Array.isArray(item))
        : [];

      const meta = dashboard.dataset_meta?.[datasetId] ?? null;
      const columns = meta?.columns?.map((column) => column.name) ?? Object.keys(normalizedRows[0] ?? {});
      const widgetMeta = datasetWidgetMeta.get(datasetId);

      const rawName = datasetId.replace(/_ds$/, "");
      const rawSegments = rawName.split("_");
      const moduleName = rawSegments[0] ?? "dataset";

      const rowCount = meta?.row_count ?? normalizedRows.length;
      const semanticKind = meta?.semantic_kind ?? "table";

      return {
        id: datasetId,
        title: widgetMeta?.title || humanize(rawName),
        moduleLabel: humanize(moduleName),
        tabId: widgetMeta?.tabId ?? fallbackTabId,
        tabTitle: widgetMeta?.tabTitle ?? tabTitleById.get(fallbackTabId) ?? humanize(fallbackTabId),
        rowCount,
        semanticKind,
        priority: widgetMeta?.priority ?? 100,
        hasChart: Boolean(widgetMeta?.chartWidget),
        previewKpis: buildPreviewKpis(normalizedRows, columns),
        rows: normalizedRows,
        columns,
        meta,
        chartWidget: widgetMeta?.chartWidget,
      } satisfies DatasetCardModel;
    })
    .sort((a, b) => a.priority - b.priority || a.title.localeCompare(b.title));
}
