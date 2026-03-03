import { cn } from "../../../lib-utils";
import { formatMaybeDate, humanize } from "../utils";

interface Props {
  datasetId: string;
  columns: string[];
  rows: Array<Record<string, unknown>>;
}

export function DatasetTable({ datasetId, columns, rows }: Props) {
  return (
    <div className="overflow-x-auto rounded-2xl border border-slate-200">
      <table className="min-w-full border-collapse text-sm">
        <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
          <tr>
            {columns.map((column) => (
              <th key={column} className="px-3 py-2 font-semibold">
                {humanize(column)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={`${datasetId}-${rowIndex}`} className="border-t border-slate-100 text-slate-700">
              {columns.map((column) => (
                <td key={column} className={cn("px-3 py-2", rowIndex % 2 === 1 && "bg-slate-50/35")}>
                  {formatMaybeDate(row[column])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
