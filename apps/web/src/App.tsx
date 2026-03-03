import { Suspense, lazy, useEffect, useRef, type ReactNode } from "react";

import { cn } from "./lib/utils";
import { AnalysesToolbar } from "./features/analyses/components/AnalysesToolbar";
import { FileUpload } from "./features/analyses/components/FileUpload";
import { HeroPanel } from "./features/analyses/components/HeroPanel";
import { ProgressView } from "./features/analyses/components/ProgressView";
import { useAnalysesScreen } from "./features/analyses/hooks/useAnalysesScreen";
import { useUrlState } from "./features/app/hooks/useUrlState";
import { I18nProvider, useI18n } from "./features/i18n/useI18n";

const ReactDashboard = lazy(async () => {
  const module = await import("./features/dashboard/components/ReactDashboard");
  return { default: module.ReactDashboard };
});

interface StatusNoticeProps {
  tone?: "info" | "error" | "warning" | "success";
  title: string;
  description?: string;
  action?: ReactNode;
}

function StatusNotice({ tone = "info", title, description, action }: StatusNoticeProps) {
  const classes = {
    info: "border-slate-200 bg-white/80 text-slate-700",
    warning: "border-amber-200 bg-amber-50/80 text-amber-900",
    error: "border-rose-200 bg-rose-50/90 text-rose-900",
    success: "border-emerald-200 bg-emerald-50/80 text-emerald-900",
  }[tone];

  return (
    <section className={cn("surface rounded-2xl border p-4", classes)}>
      <p className="font-semibold">{title}</p>
      {description && <p className="mt-1 text-sm">{description}</p>}
      {action && <div className="mt-3">{action}</div>}
    </section>
  );
}

function LanguageSwitch() {
  const { t, locale, setLocale } = useI18n();

  return (
    <div className="surface inline-flex items-center gap-1 p-1" aria-label={t("app.language")}>
      <button
        type="button"
        className={cn(
          "rounded-lg px-3 py-1.5 text-xs font-semibold",
          locale === "en" ? "bg-[var(--color-accent-strong)] text-white" : "text-slate-700 hover:bg-white"
        )}
        onClick={() => setLocale("en")}
      >
        {t("app.lang.en")}
      </button>
      <button
        type="button"
        className={cn(
          "rounded-lg px-3 py-1.5 text-xs font-semibold",
          locale === "ru" ? "bg-[var(--color-accent-strong)] text-white" : "text-slate-700 hover:bg-white"
        )}
        onClick={() => setLocale("ru")}
      >
        {t("app.lang.ru")}
      </button>
    </div>
  );
}

function FlowGuide() {
  const { t } = useI18n();

  const steps = [
    {
      id: "upload",
      title: t("flow.step.upload.title"),
      text: t("flow.step.upload.body"),
    },
    {
      id: "monitor",
      title: t("flow.step.monitor.title"),
      text: t("flow.step.monitor.body"),
    },
    {
      id: "explore",
      title: t("flow.step.explore.title"),
      text: t("flow.step.explore.body"),
    },
  ];

  return (
    <section className="surface p-4">
      <p className="text-sm font-semibold text-ink">{t("flow.title")}</p>
      <div className="mt-3 grid gap-3 md:grid-cols-3">
        {steps.map((step, index) => (
          <article key={step.id} className="rounded-xl border border-slate-200/70 bg-white/60 p-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              {index + 1}. {step.title}
            </p>
            <p className="mt-1 text-sm text-slate-700">{step.text}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

interface AppContentProps {
  urlState: ReturnType<typeof useUrlState>;
}

function AppContent({ urlState }: AppContentProps) {
  const { t } = useI18n();
  const { analysisId, setAnalysisId } = urlState;
  const dashboardRef = useRef<HTMLElement | null>(null);
  const autoScrolledForRef = useRef<string | null>(null);

  const {
    listQuery,
    createMutation,
    pendingDeleteId,
    statusQuery,
    dashboardQuery,
    startAnalysis,
    removeAnalysis,
    error,
  } = useAnalysesScreen({ analysisId, setAnalysisId });

  const hasSelectedAnalysis = Boolean(analysisId);
  const selectedIsInvalid =
    Boolean(analysisId) && Boolean(listQuery.data) && !(listQuery.data?.items ?? []).some((item) => item.analysis_id === analysisId);

  const statusLabel =
    statusQuery.data?.status === "queued"
      ? t("status.queued")
      : statusQuery.data?.status === "running"
        ? t("status.running")
        : statusQuery.data?.status === "done"
          ? t("status.done")
          : statusQuery.data?.status === "failed"
            ? t("status.failed")
            : t("common.na");

  useEffect(() => {
    if (selectedIsInvalid) {
      setAnalysisId(null);
    }
  }, [selectedIsInvalid, setAnalysisId]);

  useEffect(() => {
    if (!analysisId || statusQuery.data?.status !== "done") {
      return;
    }

    if (autoScrolledForRef.current === analysisId) {
      return;
    }

    autoScrolledForRef.current = analysisId;
    dashboardRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [analysisId, statusQuery.data?.status]);

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_15%_0%,#fdf8f3_0%,#f4f2ee_45%,#eceff7_100%)] px-4 py-5 text-slate-800 md:px-8 md:py-7">
      <div className="mx-auto max-w-7xl space-y-5">
        <header className="flex flex-wrap items-center justify-end gap-3">
          <LanguageSwitch />
        </header>

        <HeroPanel />
        <FlowGuide />

        <section className="surface p-4">
          <FileUpload onSubmit={startAnalysis} disabled={createMutation.isPending} />
        </section>

        {error && (
          <StatusNotice tone="error" title={t("state.error.title")} description={(error as Error).message || t("common.unknownError")} />
        )}

        {listQuery.isLoading && <StatusNotice title={t("analyze.list.loading")} />}

        {listQuery.data && (
          <AnalysesToolbar
            items={listQuery.data.items ?? []}
            activeAnalysisId={analysisId}
            onSelect={setAnalysisId}
            onDelete={removeAnalysis}
            deletingId={pendingDeleteId}
          />
        )}

        {hasSelectedAnalysis && !selectedIsInvalid && (
          <section className="surface p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-500">{t("analysis.current")}</p>
                <p className="mt-1 font-mono text-sm text-slate-700">{analysisId}</p>
              </div>
              <span className="rounded-full bg-[var(--color-accent-soft)] px-3 py-1 text-xs font-semibold text-[var(--color-accent-deep)]">
                {t("analysis.status")}: {statusLabel}
              </span>
            </div>

            {statusQuery.data?.status === "done" && (
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <p className="text-sm text-emerald-800">{t("analysis.ready")}</p>
                <button
                  type="button"
                  className="rounded-lg border border-emerald-300 bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-900"
                  onClick={() => dashboardRef.current?.scrollIntoView({ behavior: "smooth", block: "start" })}
                >
                  {t("analysis.openDashboard")}
                </button>
              </div>
            )}
          </section>
        )}

        {hasSelectedAnalysis && !selectedIsInvalid && statusQuery.data && statusQuery.data.status !== "done" && statusQuery.data.status !== "failed" && (
          <ProgressView status={statusQuery.data} />
        )}

        {statusQuery.data?.status === "failed" && (
          <StatusNotice
            tone="error"
            title={t("analyze.status.failed", {
              message: statusQuery.data.error_message || statusQuery.data.error_code || t("common.unknownError"),
            })}
          />
        )}

        {hasSelectedAnalysis && statusQuery.isLoading && <StatusNotice title={t("analyze.status.loading")} />}

        <section ref={dashboardRef} className="space-y-4">
          <header className="surface p-4">
            <h2 className="text-2xl font-heading text-ink">{t("dashboard.section.title")}</h2>
            <p className="mt-1 text-sm text-slate-700">{t("dashboard.section.subtitle")}</p>
          </header>

          {!hasSelectedAnalysis && (
            <StatusNotice
              title={t("dashboard.empty.title")}
              description={t("dashboard.empty.body")}
            />
          )}

          {selectedIsInvalid && (
            <StatusNotice
              title={t("dashboard.empty.title")}
              description={t("dashboard.empty.body")}
            />
          )}

          {hasSelectedAnalysis && !selectedIsInvalid && statusQuery.data?.status !== "done" && statusQuery.data?.status !== "failed" && statusQuery.data && (
            <StatusNotice tone="warning" title={t("dashboard.pending.title")} description={t("dashboard.pending.body")} />
          )}

          {hasSelectedAnalysis && !selectedIsInvalid && statusQuery.data?.status === "failed" && (
            <StatusNotice tone="error" title={t("dashboard.failed.title")} description={t("dashboard.failed.body")} />
          )}

          {hasSelectedAnalysis && !selectedIsInvalid && statusQuery.data?.status === "done" && dashboardQuery.isLoading && (
            <StatusNotice title={t("analyze.dashboard.loading")} />
          )}

          {hasSelectedAnalysis && !selectedIsInvalid && statusQuery.data?.status === "done" && dashboardQuery.data && (
            <Suspense fallback={<StatusNotice title={t("analyze.dashboard.renderer")} />}>
              <ReactDashboard dashboard={dashboardQuery.data} />
            </Suspense>
          )}
        </section>
      </div>
    </main>
  );
}

function App() {
  const urlState = useUrlState();

  return (
    <I18nProvider locale={urlState.lang} setLocale={urlState.setLang}>
      <AppContent urlState={urlState} />
    </I18nProvider>
  );
}

export default App;
