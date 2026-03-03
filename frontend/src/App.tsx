import { Suspense, lazy } from "react";

import { FileUpload } from "./components/FileUpload";
import { ProgressView } from "./components/ProgressView";
import { AnalysesToolbar } from "./features/analyses/components/AnalysesToolbar";
import { HeroPanel } from "./features/analyses/components/HeroPanel";
import { useAnalysesScreen } from "./features/analyses/hooks/useAnalysesScreen";

const ReactDashboard = lazy(async () => {
  const module = await import("./features/dashboard/components/ReactDashboard");
  return { default: module.ReactDashboard };
});

function App() {
  const {
    analysisId,
    setAnalysisId,
    listQuery,
    createMutation,
    deleteMutation,
    statusQuery,
    dashboardQuery,
    error,
  } = useAnalysesScreen();

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_10%_0%,#b1f1cf_0%,#f4efe7_42%,#cbd8f0_100%)] p-4 font-body text-slate-800 md:p-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <HeroPanel />

        <section className="rounded-2xl border border-white/50 bg-white/70 p-4 shadow-md backdrop-blur">
          <FileUpload onSubmit={(file) => createMutation.mutate(file)} disabled={createMutation.isPending} />
        </section>

        {error && (
          <section className="rounded-2xl border border-rose-300 bg-rose-50 p-4 text-sm text-rose-800">
            {(error as Error).message}
          </section>
        )}

        {listQuery.isLoading && (
          <section className="rounded-2xl border border-slate-200 bg-white/80 p-4 text-sm text-slate-600 shadow-sm">
            Loading analyses...
          </section>
        )}

        {listQuery.data && (
          <AnalysesToolbar
            items={listQuery.data.items}
            activeAnalysisId={analysisId}
            onSelect={setAnalysisId}
            onDelete={(id) => deleteMutation.mutate(id)}
            deleting={deleteMutation.isPending}
          />
        )}

        {analysisId && statusQuery.data && statusQuery.data.status !== "done" && statusQuery.data.status !== "failed" && (
          <ProgressView status={statusQuery.data} />
        )}

        {statusQuery.data?.status === "failed" && (
          <section className="rounded-2xl border border-rose-300 bg-rose-50 p-4 text-sm text-rose-800">
            Analysis failed: {statusQuery.data.error_message || statusQuery.data.error_code || "unknown error"}
          </section>
        )}

        {analysisId && statusQuery.isLoading && (
          <section className="rounded-2xl border border-slate-200 bg-white/80 p-4 text-sm text-slate-600 shadow-sm">
            Loading analysis status...
          </section>
        )}

        {statusQuery.data?.status === "done" && dashboardQuery.isLoading && (
          <section className="rounded-2xl border border-slate-200 bg-white/80 p-4 text-sm text-slate-600 shadow-sm">
            Loading dashboard...
          </section>
        )}

        {statusQuery.data?.status === "done" && dashboardQuery.data && (
          <Suspense
            fallback={
              <section className="rounded-2xl border border-slate-200 bg-white/80 p-4 text-sm text-slate-600 shadow-sm">
                Loading dashboard renderer...
              </section>
            }
          >
            <ReactDashboard dashboard={dashboardQuery.data} />
          </Suspense>
        )}
      </div>
    </main>
  );
}

export default App;
