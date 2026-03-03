import { cn } from "../../../lib/utils";

interface Props {
  label: string;
  value: string;
  compact?: boolean;
  className?: string;
}

export function KpiCard({ label, value, compact = false, className }: Props) {
  return (
    <article className={cn("surface p-4", compact && "sm:aspect-square sm:p-3", className)}>
      <p className={cn("text-xs uppercase tracking-wider text-slate-500", compact && "leading-tight")}>{label}</p>
      <p className={cn("mt-2 text-2xl font-heading text-ink", compact && "mt-3 text-3xl sm:text-2xl lg:text-3xl")}>{value}</p>
    </article>
  );
}
