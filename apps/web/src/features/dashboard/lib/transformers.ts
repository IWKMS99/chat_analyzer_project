import type { DashboardResponse, DashboardWidget } from "@chat-analyzer/api-contracts";
import type { ChartModel, DatasetCardModel, SummaryKpi } from "../model";
import { formatMaybeDate, humanize, safeString } from "./formatters";

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

function normalizeX(value: unknown): string {
  if (typeof value === "string") {
    return value;
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return "-";
}

export function summaryKpis(dashboard: DashboardResponse): SummaryKpi[] {
  const summary = dashboard.summary ?? {};
  const keys = [
    ["total_messages", "Messages"],
    ["participants", "Participants"],
    ["start", "Start"],
    ["end", "End"],
    ["timezone", "Timezone"],
  ] as const;

  return keys.map(([key, label]) => {
    const raw = summary[key];
    return {
      key,
      label,
      value: key === "start" || key === "end" ? formatMaybeDate(raw) : safeString(raw),
    };
  });
}

export function buildChartModel(rows: Array<Record<string, unknown>>, chartWidget?: DashboardWidget): ChartModel | null {
  if (!rows.length) {
    return null;
  }

  const first = rows[0] ?? {};
  const keys = Object.keys(first);
  if (!keys.length) {
    return null;
  }

  const xField =
    chartWidget?.chart_config?.x && keys.includes(chartWidget.chart_config.x)
      ? chartWidget.chart_config.x
      : keys.find((key) => rows.some((row) => parseNumeric(row[key]) === null)) ?? keys[0];

  const kind = chartWidget?.chart_config?.kind === "bar" || chartWidget?.chart_config?.kind === "histogram" ? "bar" : "line";
  const requestedY = chartWidget?.chart_config?.y;
  const requestedSeries = chartWidget?.chart_config?.series;

  const numericKeys = keys.filter((key) => key !== xField && rows.some((row) => parseNumeric(row[key]) !== null));

  if (!numericKeys.length) {
    return null;
  }

  const hasLongSeries =
    Boolean(requestedSeries) &&
    rows.some((row) => row[requestedSeries as string] !== undefined) &&
    Boolean(requestedY) &&
    rows.some((row) => parseNumeric(row[requestedY as string]) !== null);

  if (hasLongSeries) {
    const xOrder: string[] = [];
    const bucket = new Map<string, Record<string, string | number | null>>();
    const seriesSet = new Set<string>();

    rows.forEach((row) => {
      const xValue = normalizeX(row[xField]);
      const seriesValue = safeString(row[requestedSeries as string]);
      const yValue = parseNumeric(row[requestedY as string]);
      if (yValue === null) {
        return;
      }

      if (!bucket.has(xValue)) {
        bucket.set(xValue, { x: xValue });
        xOrder.push(xValue);
      }
      bucket.get(xValue)![seriesValue] = yValue;
      seriesSet.add(seriesValue);
    });

    const seriesKeys = Array.from(seriesSet);
    if (!seriesKeys.length) {
      return null;
    }

    return {
      data: xOrder.map((x) => bucket.get(x) ?? { x }),
      xKey: "x",
      seriesKeys,
      kind,
    };
  }

  const seriesKeys =
    requestedY && numericKeys.includes(requestedY) ? [requestedY, ...numericKeys.filter((key) => key !== requestedY)] : numericKeys;

  return {
    data: rows.map((row) => {
      const record: Record<string, string | number | null> = { x: normalizeX(row[xField]) };
      seriesKeys.forEach((key) => {
        record[key] = parseNumeric(row[key]);
      });
      return record;
    }),
    xKey: "x",
    seriesKeys,
    kind,
  };
}

export function buildDatasetCards(dashboard: DashboardResponse): DatasetCardModel[] {
  const chartWidgetByDataset = new Map<string, DashboardWidget>();
  for (const widget of dashboard.widgets ?? []) {
    if (widget.type === "chart" && widget.dataset) {
      chartWidgetByDataset.set(widget.dataset, widget);
    }
  }

  const entries = Object.entries(dashboard.datasets ?? {});
  return entries
    .map(([datasetId, rows]) => {
      const normalizedRows = Array.isArray(rows)
        ? rows.filter((item): item is Record<string, unknown> => !!item && typeof item === "object" && !Array.isArray(item))
        : [];

      const rawName = datasetId.replace(/_ds$/, "");
      const rawSegments = rawName.split("_");
      const moduleName = rawSegments[0] ?? "dataset";
      const moduleLabel = humanize(moduleName);

      const meta = dashboard.dataset_meta?.[datasetId] ?? null;
      const columns = meta?.columns?.map((column) => column.name) ?? Object.keys(normalizedRows[0] ?? {});

      return {
        id: datasetId,
        title: humanize(rawName),
        moduleLabel,
        rows: normalizedRows,
        columns,
        meta,
        chartWidget: chartWidgetByDataset.get(datasetId),
      };
    })
    .sort((a, b) => a.title.localeCompare(b.title));
}
