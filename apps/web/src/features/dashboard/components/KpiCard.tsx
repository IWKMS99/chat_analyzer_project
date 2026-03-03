interface Props {
  label: string;
  value: string;
}

export function KpiCard({ label, value }: Props) {
  return (
    <article className="surface p-4">
      <p className="text-xs uppercase tracking-wider text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-heading text-ink">{value}</p>
    </article>
  );
}
