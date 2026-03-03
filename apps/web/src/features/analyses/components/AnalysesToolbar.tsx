import type { AnalysisListItem } from "@chat-analyzer/api-contracts";

interface Props {
  items: AnalysisListItem[];
  activeAnalysisId: string | null;
  onSelect: (analysisId: string) => void;
  onDelete: (analysisId: string) => void;
  deleting: boolean;
}

export function AnalysesToolbar({ items, activeAnalysisId, onSelect, onDelete, deleting }: Props) {
  if (items.length === 0) {
    return null;
  }

  return (
    <section className="rounded-2xl border border-white/50 bg-white/80 p-4 shadow-md backdrop-blur">
      <p className="text-xs uppercase tracking-wide text-slate-500">Analyses</p>
      <div className="mt-2 flex flex-wrap gap-2">
        {items.map((item) => (
          <div key={item.analysis_id} className="flex items-center gap-1">
            <button
              type="button"
              className={`rounded-xl px-3 py-2 text-sm font-semibold ${
                activeAnalysisId === item.analysis_id ? "bg-ink text-white" : "bg-white text-ink hover:bg-slate-100"
              }`}
              onClick={() => onSelect(item.analysis_id)}
              aria-label={`Open analysis ${item.analysis_id}`}
            >
              {item.analysis_id.slice(0, 8)} • {item.status}
            </button>
            <button
              type="button"
              className="rounded-xl border border-slate-300 px-2 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100"
              onClick={() => onDelete(item.analysis_id)}
              disabled={deleting}
              aria-label={`Delete analysis ${item.analysis_id}`}
            >
              Delete
            </button>
          </div>
        ))}
      </div>
    </section>
  );
}
