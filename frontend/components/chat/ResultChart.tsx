"use client";

import { useMemo, useState } from "react";
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";

interface ResultChartProps {
  columns: string[];
  rows: unknown[][];
  /** The question this result answers, used to pick the column worth plotting. */
  question?: string;
}

function isNumeric(val: unknown): boolean {
  return typeof val === "number" || (typeof val === "string" && !isNaN(Number(val)) && val.trim() !== "");
}

function isDateLike(val: unknown): boolean {
  if (typeof val !== "string") return false;
  return /^\d{4}-\d{2}/.test(val);
}

/** Words that appear in almost every question and so discriminate nothing. */
const STOPWORDS = new Set([
  "the", "a", "an", "our", "my", "is", "are", "was", "were", "of", "in", "on", "for", "by",
  "to", "and", "or", "what", "which", "who", "how", "show", "me", "list", "give", "find",
  "get", "all", "each", "per", "broken", "down", "breakdown", "group", "grouped", "sorted",
  "top", "most", "least", "many", "much", "do", "does", "did", "have", "has", "with",
]);

function tokenize(text: string): string[] {
  return text
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter((t) => t.length > 1 && !STOPWORDS.has(t));
}

/**
 * Choose which numeric column to plot.
 *
 * This used to be hardcoded to `columns[1]`, which meant "what is our total
 * active MRR by plan?" charted `active_subscriptions` purely because the agent
 * happened to SELECT the count first. The chart confidently answered a
 * different question than the one asked, which is worse than showing nothing.
 *
 * Scoring the column names against the question is a heuristic, not inference:
 * `total_mrr` beats `active_subscriptions` for that question because "total"
 * and "mrr" both appear in it. Ties and no-matches fall back to the first
 * numeric column, which is the old behaviour. The picker below is the real
 * answer to the heuristic being wrong — a viewer can always switch.
 */
function pickValueColumn(columns: string[], numericCols: number[], question?: string): number {
  if (!question || numericCols.length < 2) return numericCols[0];

  const asked = new Set(tokenize(question));
  let best = numericCols[0];
  let bestScore = -1;

  for (const idx of numericCols) {
    const score = tokenize(columns[idx]).reduce((n, t) => n + (asked.has(t) ? 1 : 0), 0);
    if (score > bestScore) {
      bestScore = score;
      best = idx;
    }
  }
  return bestScore > 0 ? best : numericCols[0];
}

export function ResultChart({ columns, rows, question }: ResultChartProps) {
  const numericCols = useMemo(
    () => columns.map((_, i) => i).filter((i) => i !== 0 && isNumeric(rows[0]?.[i])),
    [columns, rows],
  );

  const [valueIdx, setValueIdx] = useState(() => pickValueColumn(columns, numericCols, question));

  const data = useMemo(
    () => rows.map((row) => ({ label: String(row[0]), value: Number(row[valueIdx]) })),
    [rows, valueIdx],
  );

  if (columns.length < 2 || rows.length < 2 || numericCols.length === 0) return null;

  const useLineChart = isDateLike(rows[0]?.[0]);
  const valueCol = columns[valueIdx];

  return (
    <div className="mt-4">
      <div className="flex items-center gap-2 mb-1 flex-wrap">
        <span className="text-xs text-muted-foreground">Charting</span>
        {numericCols.length > 1 ? (
          <select
            value={valueIdx}
            onChange={(e) => setValueIdx(Number(e.target.value))}
            aria-label="Column to chart"
            className="text-xs bg-muted rounded px-1.5 py-0.5 border border-border"
          >
            {numericCols.map((i) => (
              <option key={i} value={i}>
                {columns[i]}
              </option>
            ))}
          </select>
        ) : (
          <span className="text-xs font-medium">{valueCol}</span>
        )}
        <span className="text-xs text-muted-foreground">by {columns[0]}</span>
      </div>

      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          {useLineChart ? (
            <LineChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} width={56} />
              <Tooltip />
              <Line
                type="monotone"
                dataKey="value"
                name={valueCol}
                stroke="var(--color-primary)"
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          ) : (
            <BarChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} width={56} />
              <Tooltip />
              {/* Explicit fill: without it Recharts renders its default dark
                  bars, which read as unstyled against the rest of the UI. */}
              <Bar dataKey="value" name={valueCol} fill="var(--color-primary)" radius={[3, 3, 0, 0]} />
            </BarChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
}
