import { useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { ChartWidget, DashboardResponse, DatasetMeta } from "../../../types";
import { cn } from "../../../lib-utils";

interface Props {
  dashboard: DashboardResponse;
}

interface SummaryKpi {
  key: string;
  label: string;
  value: string;
}

interface DatasetCardModel {
  id: string;
  title: string;
  moduleLabel: string;
  rows: Array<Record<string, unknown>>;
  columns: string[];
  meta: DatasetMeta | null;
  chartWidget?: ChartWidget;
}

interface ChartModel {
  data: Array<Record<string, string | number | null>>;
  xKey: string;
  seriesKeys: string[];
  kind: "line" | "bar";
}

function humanize(value: string): string {
  return value
    .replace(/_ds$/, "")
    .split("_")
    .filter(Boolean)
    .map((part) => part[0].toUpperCase() + part.slice(1))
    .join(" ");
}

function safeString(value: unknown): string {
  if (value === null || value === undefined) {
    return "-";
  }
  if (typeof value === "number") {
    if (!Number.isFinite(value)) {
      return "-";
    }
    return value.toLocaleString();
  }
  if (typeof value === "string") {
    return value || "-";
  }
  if (typeof value === "boolean") {
    return value ? "Yes" : "No";
  }
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

function formatMaybeDate(value: unknown): string {
  if (typeof value !== "string" || !value.includes("T")) {
    return safeString(value);
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString();
}

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

function summaryKpis(dashboard: DashboardResponse): SummaryKpi[] {
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

function buildChartModel(rows: Array<Record<string, unknown>>, chartWidget?: ChartWidget): ChartModel | null {
  if (!rows.length) {
    return null;
  }

  const first = rows[0] ?? {};
  const keys = Object.keys(first);
  if (!keys.length) {
    return null;
  }

  const xField = chartWidget?.chart_config?.x && keys.includes(chartWidget.chart_config.x)
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

  const seriesKeys = requestedY && numericKeys.includes(requestedY) ? [requestedY, ...numericKeys.filter((key) => key !== requestedY)] : numericKeys;
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

function DatasetChart({ rows, chartWidget }: { rows: Array<Record<string, unknown>>; chartWidget?: ChartWidget }) {
  const model = useMemo(() => buildChartModel(rows, chartWidget), [rows, chartWidget]);

  if (!model) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
        Chart is unavailable for this dataset type.
      </div>
    );
  }

  const colors = ["#1f7a8c", "#0f766e", "#2563eb", "#ea580c", "#dc2626", "#7c3aed"];

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-2">
      <div className="h-[300px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          {model.kind === "bar" ? (
            <BarChart data={model.data} margin={{ top: 8, right: 12, left: 0, bottom: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey={model.xKey} tick={{ fontSize: 11, fill: "#475569" }} />
              <YAxis tick={{ fontSize: 11, fill: "#475569" }} />
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: "12px" }} />
              {model.seriesKeys.map((seriesKey, idx) => (
                <Bar key={seriesKey} dataKey={seriesKey} fill={colors[idx % colors.length]} radius={[4, 4, 0, 0]} />
              ))}
            </BarChart>
          ) : (
            <LineChart data={model.data} margin={{ top: 8, right: 12, left: 0, bottom: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey={model.xKey} tick={{ fontSize: 11, fill: "#475569" }} />
              <YAxis tick={{ fontSize: 11, fill: "#475569" }} />
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: "12px" }} />
              {model.seriesKeys.map((seriesKey, idx) => (
                <Line
                  key={seriesKey}
                  dataKey={seriesKey}
                  type="monotone"
                  stroke={colors[idx % colors.length]}
                  strokeWidth={2}
                  dot={false}
                  connectNulls
                />
              ))}
            </LineChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export function ReactDashboard({ dashboard }: Props) {
  const [expandedTable, setExpandedTable] = useState<Record<string, boolean>>({});

  const kpis = useMemo(() => summaryKpis(dashboard), [dashboard]);
  const chartWidgetByDataset = useMemo(() => {
    const out = new Map<string, ChartWidget>();
    for (const widget of dashboard.widgets ?? []) {
      if (widget.type === "chart") {
        out.set(widget.dataset, widget as ChartWidget);
      }
    }
    return out;
  }, [dashboard.widgets]);

  const datasetCards = useMemo<DatasetCardModel[]>(() => {
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
  }, [dashboard, chartWidgetByDataset]);

  const warnings = Array.isArray(dashboard.metadata?.warnings) ? dashboard.metadata.warnings : [];

  return (
    <section className="space-y-6">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        {kpis.map((item) => (
          <article key={item.key} className="rounded-2xl border border-white/50 bg-white/80 p-4 shadow-sm backdrop-blur">
            <p className="text-xs uppercase tracking-wider text-slate-500">{item.label}</p>
            <p className="mt-2 text-2xl font-heading text-ink">{item.value}</p>
          </article>
        ))}
      </div>

      <section className="rounded-2xl border border-slate-200 bg-white/85 p-4 shadow-sm">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-600">
          <span>Analysis: {dashboard.analysis_id}</span>
          <span>Generated: {safeString(dashboard.metadata?.generated_at)}</span>
          <span>Duration: {safeString(dashboard.metadata?.duration_sec)} sec</span>
          <span>Datasets: {datasetCards.length}</span>
        </div>
      </section>

      {warnings.length > 0 && (
        <section className="rounded-2xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
          <p className="font-semibold">Warnings</p>
          <ul className="mt-2 list-disc pl-5">
            {warnings.map((warning) => (
              <li key={String(warning)}>{String(warning)}</li>
            ))}
          </ul>
        </section>
      )}

      {datasetCards.length === 0 && (
        <section className="rounded-2xl border border-slate-200 bg-white/80 p-6 text-sm text-slate-600 shadow-sm">No datasets available in this analysis.</section>
      )}

      <div className="grid gap-5 xl:grid-cols-2">
        {datasetCards.map((dataset) => {
          const previewRows = expandedTable[dataset.id] ? dataset.rows : dataset.rows.slice(0, 8);
          return (
            <article key={dataset.id} className="overflow-hidden rounded-3xl border border-slate-200 bg-white/90 shadow-sm">
              <header className="border-b border-slate-100 bg-[linear-gradient(130deg,#f7fbff,#ecf4ff)] px-5 py-4">
                <p className="text-xs font-semibold uppercase tracking-wider text-ocean">{dataset.moduleLabel}</p>
                <h3 className="mt-1 text-xl font-heading text-ink">{dataset.title}</h3>
                <p className="mt-1 text-xs text-slate-600">
                  {dataset.rows.length} rows
                  {dataset.meta ? ` | ${dataset.meta.semantic_kind}` : ""}
                </p>
              </header>

              <div className="space-y-4 p-5">
                <DatasetChart rows={dataset.rows} chartWidget={dataset.chartWidget} />

                <div className="overflow-x-auto rounded-2xl border border-slate-200">
                  <table className="min-w-full border-collapse text-sm">
                    <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                      <tr>
                        {dataset.columns.map((column) => (
                          <th key={column} className="px-3 py-2 font-semibold">
                            {humanize(column)}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {previewRows.map((row, rowIndex) => (
                        <tr key={`${dataset.id}-${rowIndex}`} className="border-t border-slate-100 text-slate-700">
                          {dataset.columns.map((column) => (
                            <td key={column} className={cn("px-3 py-2", rowIndex % 2 === 1 && "bg-slate-50/35")}>
                              {formatMaybeDate(row[column])}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {dataset.rows.length > 8 && (
                  <button
                    type="button"
                    className="text-sm font-semibold text-ocean hover:text-ink"
                    onClick={() => setExpandedTable((current) => ({ ...current, [dataset.id]: !current[dataset.id] }))}
                  >
                    {expandedTable[dataset.id] ? "Show fewer rows" : `Show all rows (${dataset.rows.length})`}
                  </button>
                )}
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
