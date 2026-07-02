"use client";

interface ResultTableProps {
  columns: string[];
  rows: unknown[][];
  truncated: boolean;
}

export function ResultTable({ columns, rows, truncated }: ResultTableProps) {
  if (!columns.length) return null;

  return (
    <div className="mt-3 overflow-x-auto rounded-lg border text-sm">
      <table className="w-full border-collapse">
        <thead>
          <tr className="bg-muted/50">
            {columns.map((col) => (
              <th key={col} className="px-3 py-2 text-left font-medium text-muted-foreground whitespace-nowrap border-b">
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b last:border-0 hover:bg-muted/20">
              {row.map((cell, j) => (
                <td key={j} className="px-3 py-2 whitespace-nowrap">
                  {cell === null ? <span className="text-muted-foreground italic">null</span> : String(cell)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {truncated && (
        <p className="px-3 py-2 text-xs text-muted-foreground bg-muted/30 border-t">
          Results truncated — showing first {rows.length} rows.
        </p>
      )}
    </div>
  );
}
