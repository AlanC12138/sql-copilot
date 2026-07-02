"use client";

import { BarChart, Bar, LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";

interface ResultChartProps {
  columns: string[];
  rows: unknown[][];
}

function isNumeric(val: unknown): boolean {
  return typeof val === "number" || (typeof val === "string" && !isNaN(Number(val)) && val.trim() !== "");
}

function isDateLike(val: unknown): boolean {
  if (typeof val !== "string") return false;
  return /^\d{4}-\d{2}/.test(val);
}

export function ResultChart({ columns, rows }: ResultChartProps) {
  if (columns.length < 2 || rows.length < 2) return null;

  const [labelCol, valueCol] = columns;
  const firstValue = rows[0]?.[1];
  if (!isNumeric(firstValue)) return null;

  const data = rows.map((row) => ({
    label: String(row[0]),
    value: Number(row[1]),
  }));

  const useLineChart = isDateLike(rows[0]?.[0]);

  return (
    <div className="mt-4 h-56">
      <ResponsiveContainer width="100%" height="100%">
        {useLineChart ? (
          <LineChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 4 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
            <XAxis dataKey="label" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip />
            <Line type="monotone" dataKey="value" name={valueCol} strokeWidth={2} dot={false} />
          </LineChart>
        ) : (
          <BarChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 4 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
            <XAxis dataKey="label" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip />
            <Bar dataKey="value" name={valueCol} radius={[3, 3, 0, 0]} />
          </BarChart>
        )}
      </ResponsiveContainer>
    </div>
  );
}
