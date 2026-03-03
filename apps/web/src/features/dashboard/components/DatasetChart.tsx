import { useMemo } from "react";
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

import type { DashboardWidget } from "@chat-analyzer/api-contracts";
import { buildChartModel } from "../utils";

interface Props {
  rows: Array<Record<string, unknown>>;
  chartWidget?: DashboardWidget;
}

export function DatasetChart({ rows, chartWidget }: Props) {
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
