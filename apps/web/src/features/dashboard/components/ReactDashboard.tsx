import { useMemo, useState } from "react";

import type { DashboardResponse } from "@chat-analyzer/api-contracts";
import { DatasetChart } from "./DatasetChart";
import { DatasetTable } from "./DatasetTable";
import { KpiCard } from "./KpiCard";
import { safeString } from "../lib/formatters";
import { buildDatasetCards, summaryKpis } from "../lib/transformers";

interface Props {
  dashboard: DashboardResponse;
}

export function ReactDashboard({ dashboard }: Props) {
  const [expandedTable, setExpandedTable] = useState<Record<string, boolean>>({});
  const kpis = useMemo(() => summaryKpis(dashboard), [dashboard]);
  const datasetCards = useMemo(() => buildDatasetCards(dashboard), [dashboard]);
  const warnings = Array.isArray(dashboard.metadata?.warnings) ? dashboard.metadata.warnings : [];

  return (
    <section className="space-y-6">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        {kpis.map((item) => (
          <KpiCard key={item.key} label={item.label} value={item.value} />
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
        <section className="rounded-2xl border border-slate-200 bg-white/80 p-6 text-sm text-slate-600 shadow-sm">
          No datasets available in this analysis.
        </section>
      )}

      <div className="grid gap-5 xl:grid-cols-2">
        {datasetCards.map((dataset) => {
          const isExpanded = Boolean(expandedTable[dataset.id]);
          const previewRows = isExpanded ? dataset.rows : dataset.rows.slice(0, 8);

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
                <DatasetTable datasetId={dataset.id} columns={dataset.columns} rows={previewRows} />

                {dataset.rows.length > 8 && (
                  <button
                    type="button"
                    className="text-sm font-semibold text-ocean hover:text-ink"
                    onClick={() => setExpandedTable((current) => ({ ...current, [dataset.id]: !current[dataset.id] }))}
                  >
                    {isExpanded ? "Show fewer rows" : `Show all rows (${dataset.rows.length})`}
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
