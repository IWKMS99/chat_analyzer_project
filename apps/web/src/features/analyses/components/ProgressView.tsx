import type { AnalysisStatusResponse } from "@chat-analyzer/api-contracts";

interface Props {
  status: AnalysisStatusResponse;
}

export function ProgressView({ status }: Props) {
  const warnings = status.warnings ?? [];

  return (
    <div className="mx-auto max-w-2xl rounded-3xl border border-white/30 bg-white/70 p-8 shadow-xl backdrop-blur-sm">
      <h2 className="font-heading text-2xl text-ink">Analysis in progress</h2>
      <p className="mt-1 text-sm text-slate-700">Phase: {status.phase}</p>
      <div className="mt-6 h-4 w-full overflow-hidden rounded-full bg-slate-200">
        <div className="h-full rounded-full bg-ocean transition-all" style={{ width: `${status.progress_pct}%` }} />
      </div>
      <p className="mt-2 text-sm text-slate-700">{status.progress_pct}%</p>
      {warnings.length > 0 && (
        <ul className="mt-4 list-disc pl-5 text-sm text-amber-700">
          {warnings.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
