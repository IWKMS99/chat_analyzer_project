import { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, LayoutGroup, motion } from "framer-motion";

import type { DashboardResponse, DatasetMetaRecommendedWidget } from "@chat-analyzer/api-contracts";
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

function explainerKey(semanticKind: string) {
  if (semanticKind === "time_series") {
    return "dashboard.tile.explainer.time_series" as const;
  }
  if (semanticKind === "distribution") {
    return "dashboard.tile.explainer.distribution" as const;
  }
  if (semanticKind === "categorical_breakdown") {
    return "dashboard.tile.explainer.categorical_breakdown" as const;
  }
  if (semanticKind === "network_edges") {
    return "dashboard.tile.explainer.network_edges" as const;
  }
  if (semanticKind === "fallback") {
    return "dashboard.tile.explainer.fallback" as const;
  }
  return "dashboard.tile.explainer.default" as const;
}

function recommendedWidgetLabel(value: DatasetMetaRecommendedWidget | undefined | null): string {
  if (value === "both") {
    return "chart + table";
  }
  if (value === "chart") {
    return "chart";
  }
  if (value === "table") {
    return "table";
  }
  return "chart + table";
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

      <section className="surface p-4">
        <p className="text-sm font-semibold text-ink">{t("dashboard.guide.title")}</p>
        <div className="mt-3 grid gap-3 md:grid-cols-2">
          <article className="rounded-xl border border-slate-200/70 bg-white/60 p-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t("dashboard.guide.everyone.title")}</p>
            <p className="mt-1 text-sm text-slate-700">{t("dashboard.guide.everyone.body")}</p>
          </article>
          <article className="rounded-xl border border-slate-200/70 bg-white/60 p-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t("dashboard.guide.analyst.title")}</p>
            <p className="mt-1 text-sm text-slate-700">{t("dashboard.guide.analyst.body")}</p>
          </article>
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

          <LayoutGroup id={`dashboard-${section.id}`}>
            <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
              {section.cards.map((dataset) => {
                const isExpanded = Boolean(expandedCards[dataset.id]);
                const isTableExpanded = Boolean(expandedTable[dataset.id]);
                const isLoading = Boolean(loadingCards[dataset.id]);
                const previewRows = isTableExpanded ? dataset.rows : dataset.rows.slice(0, 8);

                return (
                  <motion.article
                    layout
                    key={dataset.id}
                    className="surface-elevated overflow-hidden p-4"
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
                        <span className="rounded-full bg-white px-2 py-1 text-xs text-slate-700">{t("dashboard.tile.semantic", { value: dataset.semanticKind })}</span>
                        <span className="rounded-full bg-white px-2 py-1 text-xs text-slate-700">
                          {t("dashboard.tile.recommended", { value: recommendedWidgetLabel(dataset.meta?.recommended_widget) })}
                        </span>
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

                      <motion.div
                        layoutId={`dataset-accent-${dataset.id}`}
                        className="mt-3 h-14 rounded-xl bg-[linear-gradient(110deg,rgba(217,232,255,0.75),rgba(255,255,255,0.92))]"
                      />

                      <p className="mt-2 text-xs text-slate-600">{t(explainerKey(dataset.semanticKind))}</p>
                      <p className="mt-2 text-xs font-semibold text-[var(--color-accent-deep)]">
                        {isExpanded ? t("dashboard.tile.close") : t("dashboard.tile.open")}
                      </p>
                    </button>

                    <AnimatePresence initial={false}>
                      {isExpanded && (
                        <motion.section
                          key={`${dataset.id}-details`}
                          id={`dataset-panel-${dataset.id}`}
                          layout
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: "auto", opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          transition={{ type: "spring", stiffness: 300, damping: 33, mass: 0.7 }}
                          className="overflow-hidden"
                        >
                          <div className="mt-4 space-y-4 border-t border-slate-200 pt-4">
                            <motion.div layoutId={`dataset-accent-${dataset.id}`} className="h-1 rounded-full bg-[var(--color-accent-strong)]" />

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
          </LayoutGroup>
        </section>
      ))}
    </section>
  );
}
