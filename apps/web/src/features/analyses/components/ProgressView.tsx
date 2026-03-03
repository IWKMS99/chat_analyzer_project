import type { AnalysisStatusResponse } from "@chat-analyzer/api-contracts";

import type { TranslationKey } from "../../i18n/dictionary";
import { useI18n } from "../../i18n/useI18n";

interface Props {
  status: AnalysisStatusResponse;
}

const PHASE_KEY: Record<AnalysisStatusResponse["phase"], TranslationKey> = {
  parsing: "phase.parsing",
  analyzing: "phase.analyzing",
  serializing: "phase.serializing",
  storing: "phase.storing",
  done: "phase.done",
  failed: "phase.failed",
};

function resolveNarrativeKey(progressPct: number): TranslationKey {
  if (progressPct < 20) {
    return "analyze.status.narrative.unpacking";
  }
  if (progressPct < 50) {
    return "analyze.status.narrative.nightOwls";
  }
  if (progressPct < 80) {
    return "analyze.status.narrative.emoji";
  }
  return "analyze.status.narrative.charts";
}

export function ProgressView({ status }: Props) {
  const { t } = useI18n();
  const warnings = status.warnings ?? [];
  const narrativeKey = resolveNarrativeKey(status.progress_pct);

  return (
    <section className="surface-elevated mx-auto max-w-3xl p-6">
      <h2 className="text-xl font-heading text-ink">{t("analyze.status.inProgress")}</h2>
      <p className="mt-1 text-sm text-slate-700">{t(narrativeKey)}</p>
      <p className="mt-1 text-xs text-slate-500">{t("analyze.status.phase", { phase: t(PHASE_KEY[status.phase]) })}</p>

      <div className="mt-5 h-3 w-full overflow-hidden rounded-full bg-slate-200">
        <div className="h-full rounded-full bg-[var(--color-accent-strong)] transition-all duration-500" style={{ width: `${status.progress_pct}%` }} />
      </div>
      <p className="mt-2 text-sm text-slate-700">{t("analyze.status.progress", { value: status.progress_pct })}</p>

      {warnings.length > 0 && (
        <div className="mt-5 rounded-xl border border-amber-200 bg-amber-50/80 p-3 text-sm text-amber-800">
          <p className="font-semibold">{t("state.warnings")}</p>
          <ul className="mt-2 list-disc pl-5">
            {warnings.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
