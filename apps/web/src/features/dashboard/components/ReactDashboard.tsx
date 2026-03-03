import { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";

import type { DashboardResponse } from "@chat-analyzer/api-contracts";
import type { DatasetCardModel } from "../model";
import { useI18n } from "../../i18n/useI18n";
import { DatasetChart } from "./DatasetChart";
import { DatasetTable } from "./DatasetTable";
import { KpiCard } from "./KpiCard";
import { safeString } from "../lib/formatters";
import { buildDatasetCards, summaryKpis } from "../lib/transformers";

interface Props {
  dashboard: DashboardResponse;
}

interface TabGroup {
  id: string;
  title: string;
  order: number;
}

function explanationKeyForDataset(dataset: DatasetCardModel) {
  const source = `${dataset.id} ${dataset.title} ${dataset.moduleLabel}`.toLowerCase();

  if (source.includes("hourly") || source.includes("hour")) return "dashboard.explain.hourly" as const;
  if (source.includes("daily") || source.includes("day")) return "dashboard.explain.daily" as const;
  if (source.includes("weekday")) return "dashboard.explain.weekday" as const;
  if (source.includes("monthly") || source.includes("month")) return "dashboard.explain.monthly" as const;
  if (source.includes("period")) return "dashboard.explain.periods" as const;
  if (source.includes("anomal")) return "dashboard.explain.anomaly" as const;
  if (source.includes("emoji")) return "dashboard.explain.emoji" as const;
  if (source.includes("keyword")) return "dashboard.explain.keywords" as const;
  if (source.includes("sentiment")) return "dashboard.explain.sentiment" as const;
  if (source.includes("question_ratio") || source.includes("question ratio")) return "dashboard.explain.questions" as const;
  if (source.includes("length")) return "dashboard.explain.lengths" as const;
  if (source.includes("reply_edges") || source.includes("reaction_edges")) return "dashboard.explain.edges" as const;
  if (source.includes("pair_median")) return "dashboard.explain.pairMedian" as const;
  if (source.includes("response") || source.includes("interval")) return "dashboard.explain.response" as const;
  if (source.includes("sessions")) return "dashboard.explain.sessions" as const;
  if (source.includes("message_counts")) return "dashboard.explain.userCounts" as const;
  if (source.includes("avg_length")) return "dashboard.explain.userAvgLength" as const;
  if (source.includes("chains")) return "dashboard.explain.userChains" as const;
  if (source.includes("vocabulary")) return "dashboard.explain.vocabulary" as const;

  if (dataset.semanticKind === "time_series") return "dashboard.semantic.time_series" as const;
  if (dataset.semanticKind === "distribution") return "dashboard.semantic.distribution" as const;
  if (dataset.semanticKind === "categorical_breakdown") return "dashboard.semantic.categorical_breakdown" as const;
  if (dataset.semanticKind === "network_edges") return "dashboard.semantic.network_edges" as const;
  return "dashboard.semantic.fallback" as const;
}

function DatasetSkeleton() {
  return (
    <div className="space-y-3" aria-hidden="true">
      <div className="h-8 w-1/3 animate-pulse rounded bg-slate-100" />
      <div className="h-48 animate-pulse rounded-2xl bg-slate-100" />
      <div className="h-6 w-2/5 animate-pulse rounded bg-slate-100" />
      <div className="h-24 animate-pulse rounded-2xl bg-slate-100" />
    </div>
  );
}

export function ReactDashboard({ dashboard }: Props) {
  const { t } = useI18n();
  const [expandedCards, setExpandedCards] = useState<Record<string, boolean>>({});
  const [expandedTable, setExpandedTable] = useState<Record<string, boolean>>({});
  const [loadingCards, setLoadingCards] = useState<Record<string, boolean>>({});
  const loadingTimers = useRef<Record<string, ReturnType<typeof setTimeout>>>({});

  const kpis = useMemo(() => summaryKpis(dashboard), [dashboard]);
  const datasetCards = useMemo(() => buildDatasetCards(dashboard), [dashboard]);
  const warnings = Array.isArray(dashboard.metadata?.warnings) ? dashboard.metadata.warnings : [];

  const tabGroups = useMemo<TabGroup[]>(() => {
    const base = (dashboard.tabs ?? [])
      .map((tab) => ({ id: tab.id, title: tab.title, order: tab.order }))
      .sort((a, b) => a.order - b.order);

    if (!base.length) {
      return [{ id: "all", title: t("dashboard.module.fallback"), order: 0 }];
    }

    return base;
  }, [dashboard.tabs, t]);

  const groupedSections = useMemo(() => {
    const knownTabIds = new Set(tabGroups.map((tab) => tab.id));
    const fallbackTabId = tabGroups[0]?.id ?? "all";
    const cardGroup = new Map<string, typeof datasetCards>();

    tabGroups.forEach((tab) => cardGroup.set(tab.id, []));

    datasetCards.forEach((dataset) => {
      const tabId = knownTabIds.has(dataset.tabId) ? dataset.tabId : fallbackTabId;
      const bucket = cardGroup.get(tabId);
      if (!bucket) {
        cardGroup.set(tabId, [dataset]);
      } else {
        bucket.push(dataset);
      }
    });

    return tabGroups
      .map((tab) => ({
        id: tab.id,
        title: tab.title,
        cards: cardGroup.get(tab.id) ?? [],
      }))
      .filter((section) => section.cards.length > 0);
  }, [datasetCards, tabGroups]);

  useEffect(() => {
    return () => {
      Object.values(loadingTimers.current).forEach((timer) => clearTimeout(timer));
    };
  }, []);

  const toggleCard = (datasetId: string) => {
    setExpandedCards((current) => {
      const isOpening = !current[datasetId];
      const next = { ...current, [datasetId]: isOpening };

      if (isOpening) {
        setLoadingCards((loading) => ({ ...loading, [datasetId]: true }));
        if (loadingTimers.current[datasetId]) {
          clearTimeout(loadingTimers.current[datasetId]);
        }
        loadingTimers.current[datasetId] = setTimeout(() => {
          setLoadingCards((loading) => ({ ...loading, [datasetId]: false }));
        }, 360);
      } else {
        setLoadingCards((loading) => ({ ...loading, [datasetId]: false }));
      }

      return next;
    });
  };

  return (
    <section className="space-y-6">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        {kpis.map((item) => {
          const label =
            item.key === "total_messages"
              ? t("kpi.total_messages")
              : item.key === "participants"
                ? t("kpi.participants")
                : item.key === "start"
                  ? t("kpi.start")
                  : item.key === "end"
                    ? t("kpi.end")
                    : item.key === "timezone"
                      ? t("kpi.timezone")
                      : item.key;
          return <KpiCard key={item.key} label={label} value={item.value} />;
        })}
      </div>

      <section className="surface p-4">
        <p className="text-sm font-semibold text-ink">{t("dashboard.summary.title")}</p>
        <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-600">
          <span>
            {t("dashboard.summary.analysis")}: {dashboard.analysis_id}
          </span>
          <span>
            {t("dashboard.summary.generated")}: {safeString(dashboard.metadata?.generated_at)}
          </span>
          <span>
            {t("dashboard.summary.duration")}: {t("dashboard.summary.durationSec", { value: safeString(dashboard.metadata?.duration_sec) })}
          </span>
          <span>
            {t("dashboard.summary.datasets")}: {datasetCards.length}
          </span>
        </div>
      </section>

      {warnings.length > 0 && (
        <section className="surface rounded-2xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
          <p className="font-semibold">{t("state.warnings")}</p>
          <ul className="mt-2 list-disc pl-5">
            {warnings.map((warning) => (
              <li key={String(warning)}>{String(warning)}</li>
            ))}
          </ul>
        </section>
      )}

      {datasetCards.length === 0 && <section className="surface-muted p-5 text-sm text-slate-600">{t("dashboard.noDatasets")}</section>}

      {groupedSections.map((section) => (
        <section key={section.id} className="space-y-3">
          <header className="px-1">
            <h3 className="text-xl font-heading text-ink">{section.title}</h3>
          </header>

          <div className="grid items-start gap-4 md:grid-cols-2 2xl:grid-cols-3">
              {section.cards.map((dataset) => {
                const isExpanded = Boolean(expandedCards[dataset.id]);
                const isTableExpanded = Boolean(expandedTable[dataset.id]);
                const isLoading = Boolean(loadingCards[dataset.id]);
                const previewRows = isTableExpanded ? dataset.rows : dataset.rows.slice(0, 8);

                return (
                  <motion.article
                    layout="size"
                    key={dataset.id}
                    className="surface-elevated self-start overflow-hidden p-4"
                    transition={{ type: "spring", stiffness: 360, damping: 34, mass: 0.65 }}
                  >
                    <button
                      type="button"
                      className="w-full text-left"
                      aria-expanded={isExpanded}
                      aria-controls={`dataset-panel-${dataset.id}`}
                      onClick={() => toggleCard(dataset.id)}
                    >
                      <div className="flex flex-wrap items-start justify-between gap-2">
                        <div>
                          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{dataset.moduleLabel}</p>
                          <h3 className="mt-1 text-lg font-heading text-ink">{dataset.title}</h3>
                        </div>
                        <span className="rounded-full bg-[var(--color-accent-soft)] px-2 py-1 text-xs font-semibold text-[var(--color-accent-deep)]">
                          {t("dashboard.tile.rows", { count: dataset.rowCount })}
                        </span>
                      </div>

                      <div className="mt-3 flex flex-wrap gap-2">
                        <span className="rounded-full bg-slate-100 px-2 py-1 text-xs text-slate-700">{t("dashboard.tile.columns", { count: dataset.columns.length })}</span>
                      </div>

                      {dataset.previewKpis.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-2">
                          {dataset.previewKpis.map((metric) => (
                            <span key={metric.key} className="rounded-full bg-slate-50 px-2 py-1 text-xs text-slate-600">
                              {metric.label}: {metric.value}
                            </span>
                          ))}
                        </div>
                      )}

                      <p className="mt-2 text-xs text-slate-600">
                        {t("dashboard.tile.whatShows", { title: dataset.title, value: t(explanationKeyForDataset(dataset)) })}
                      </p>

                      <div
                        className="mt-3 flex items-center justify-between rounded-xl border border-[var(--color-accent-soft)] bg-[linear-gradient(110deg,rgba(217,232,255,0.92),rgba(255,255,255,0.98))] px-3 py-2 text-sm font-semibold text-[var(--color-accent-deep)] transition hover:border-[var(--color-accent-strong)] hover:shadow-sm"
                      >
                        <span>{t("dashboard.tile.open")}</span>
                        <span aria-hidden="true" className="text-base leading-none">
                          {isExpanded ? "−" : "+"}
                        </span>
                      </div>
                    </button>

                    <AnimatePresence initial={false}>
                      {isExpanded && (
                        <motion.section
                          key={`${dataset.id}-details`}
                          id={`dataset-panel-${dataset.id}`}
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: "auto", opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          transition={{ type: "spring", stiffness: 300, damping: 33, mass: 0.7 }}
                          className="overflow-hidden"
                        >
                          <div className="mt-4 space-y-4 border-t border-slate-200 pt-4">
                            <div className="h-1 rounded-full bg-[var(--color-accent-strong)]" />

                            {isLoading ? (
                              <DatasetSkeleton />
                            ) : (
                              <>
                                <DatasetChart rows={dataset.rows} chartWidget={dataset.chartWidget} />
                                <DatasetTable datasetId={dataset.id} columns={dataset.columns} rows={previewRows} />

                                {dataset.rows.length > 8 && (
                                  <button
                                    type="button"
                                    className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
                                    onClick={() =>
                                      setExpandedTable((current) => ({
                                        ...current,
                                        [dataset.id]: !current[dataset.id],
                                      }))
                                    }
                                  >
                                    {isTableExpanded
                                      ? t("dashboard.tile.showFewer")
                                      : t("dashboard.tile.showAll", { count: dataset.rows.length })}
                                  </button>
                                )}
                              </>
                            )}
                          </div>
                        </motion.section>
                      )}
                    </AnimatePresence>
                  </motion.article>
                );
              })}
            </div>
        </section>
      ))}
    </section>
  );
}
