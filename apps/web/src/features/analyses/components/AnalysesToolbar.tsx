import type { AnalysisListItem } from "@chat-analyzer/api-contracts";

import { cn } from "../../../lib/utils";
import { useI18n } from "../../i18n/useI18n";

interface Props {
  items: AnalysisListItem[];
  activeAnalysisId: string | null;
  onSelect: (analysisId: string) => void;
  onDelete: (analysisId: string) => void;
  deletingId: string | null;
}

const STATUS_CLASS: Record<string, string> = {
  queued: "bg-slate-100 text-slate-700",
  running: "bg-amber-100 text-amber-800",
  done: "bg-emerald-100 text-emerald-800",
  failed: "bg-rose-100 text-rose-700",
};

export function AnalysesToolbar({ items, activeAnalysisId, onSelect, onDelete, deletingId }: Props) {
  const { t } = useI18n();

  return (
    <section className="surface p-4">
      <p className="text-sm font-semibold text-ink">{t("analyze.list.title")}</p>

      {items.length === 0 && <p className="mt-2 text-sm text-slate-600">{t("analyze.list.empty")}</p>}

      {items.length > 0 && (
        <div className="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {items.map((item) => {
            const active = activeAnalysisId === item.analysis_id;
            const statusLabel =
              item.status === "queued"
                ? t("status.queued")
                : item.status === "running"
                  ? t("status.running")
                  : item.status === "done"
                    ? t("status.done")
                    : item.status === "failed"
                      ? t("status.failed")
                      : item.status;

            return (
              <article
                key={item.analysis_id}
                className={cn(
                  "rounded-2xl border p-3 transition",
                  active ? "border-[var(--color-accent-strong)] bg-[var(--color-accent-soft)]/35" : "border-slate-200 bg-white/70"
                )}
              >
                <button
                  type="button"
                  className="w-full text-left"
                  onClick={() => onSelect(item.analysis_id)}
                  aria-label={`Open analysis ${item.analysis_id}`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <p className="font-mono text-sm text-slate-700">{item.analysis_id.slice(0, 8)}</p>
                    <span className={cn("rounded-full px-2 py-1 text-xs font-semibold", STATUS_CLASS[item.status] || STATUS_CLASS.queued)}>
                      {statusLabel}
                    </span>
                  </div>
                  <p className="mt-2 text-xs text-slate-500">{t("analyze.list.created", { value: new Date(item.created_at).toLocaleString() })}</p>
                </button>

                <button
                  type="button"
                  className="mt-3 rounded-lg border border-slate-300 px-2 py-1 text-xs font-semibold text-slate-700 transition hover:bg-slate-100 disabled:opacity-50"
                  onClick={() => {
                    const ok = window.confirm(t("analyze.list.deleteConfirm", { id: item.analysis_id.slice(0, 8) }));
                    if (ok) {
                      onDelete(item.analysis_id);
                    }
                  }}
                  disabled={Boolean(deletingId)}
                  aria-label={`Delete analysis ${item.analysis_id}`}
                >
                  {deletingId === item.analysis_id ? `${t("analyze.list.delete")}...` : t("analyze.list.delete")}
                </button>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
