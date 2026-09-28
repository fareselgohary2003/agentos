"use client";

import React, { useState, useMemo } from "react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  AreaChart,
  Area,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from "recharts";
import {
  IconChartBar,
  IconChartLine,
  IconChartPie,
  IconTable,
  IconDownload,
  IconCode,
  IconCopy,
  IconCheck,
} from "./Icons";

interface DataVisualizerProps {
  data: {
    columns?: string[];
    rows?: (string | number | boolean | null)[][];
    row_count?: number;
    sql_used?: string;
    [key: string]: any;
  };
  title?: string;
}

// Professional, eye-friendly palette (Soft Blue, Emerald, Amber, Purple, Teal, Rose)
const PALETTE = [
  "#3b82f6", // Blue
  "#10b981", // Emerald
  "#f59e0b", // Amber
  "#8b5cf6", // Purple
  "#06b6d4", // Cyan/Teal
  "#ec4899", // Soft Rose
  "#64748b", // Slate
  "#6366f1", // Indigo
];

export default function DataVisualizer({ data, title = "Query Result Visualization" }: DataVisualizerProps) {
  const [viewType, setViewType] = useState<"bar" | "line" | "area" | "pie" | "table">("bar");
  const [search, setSearch] = useState("");
  const [showSql, setShowSql] = useState(false);
  const [copiedSql, setCopiedSql] = useState(false);

  // Normalize columns and rows
  const columns: string[] = useMemo(() => {
    if (data?.columns && Array.isArray(data.columns)) return data.columns;
    if (Array.isArray(data) && data.length > 0 && typeof data[0] === "object") {
      return Object.keys(data[0]);
    }
    return [];
  }, [data]);

  const rawRows: any[][] = useMemo(() => {
    if (data?.rows && Array.isArray(data.rows)) return data.rows;
    if (Array.isArray(data) && data.length > 0 && typeof data[0] === "object") {
      return data.map((item) => columns.map((col) => item[col]));
    }
    return [];
  }, [data, columns]);

  // Convert to array of objects for Recharts
  const chartData = useMemo(() => {
    return rawRows.map((row) => {
      const obj: Record<string, any> = {};
      columns.forEach((col, i) => {
        const val = row[i];
        if (typeof val === "number") {
          obj[col] = val;
        } else if (typeof val === "string" && !isNaN(Number(val)) && val.trim() !== "") {
          obj[col] = parseFloat(val);
        } else {
          obj[col] = val ?? "—";
        }
      });
      return obj;
    });
  }, [rawRows, columns]);

  // Detect numeric and categorical columns
  const { numericCols, categoryCols } = useMemo(() => {
    if (chartData.length === 0) return { numericCols: [], categoryCols: [] };
    const numCols: string[] = [];
    const catCols: string[] = [];

    columns.forEach((col) => {
      const sample = chartData.find((r) => r[col] !== null && r[col] !== undefined);
      if (sample && typeof sample[col] === "number") {
        numCols.push(col);
      } else {
        catCols.push(col);
      }
    });

    return { numericCols: numCols, categoryCols: catCols };
  }, [chartData, columns]);

  // Selected X and Y axes
  const [xAxisKey, setXAxisKey] = useState<string>("");
  const [metricKey, setMetricKey] = useState<string>("");

  const activeXKey = xAxisKey || (categoryCols[0] ?? columns[0] ?? "");
  const activeMetricKey = metricKey || (numericCols[0] ?? columns[columns.length - 1] ?? "");

  // Aggregated data for charts if there are duplicate X keys
  const aggregatedChartData = useMemo(() => {
    if (!activeXKey || !activeMetricKey) return chartData;
    const map = new Map<string, number>();
    chartData.forEach((row) => {
      const key = String(row[activeXKey] ?? "Unknown");
      const val = typeof row[activeMetricKey] === "number" ? row[activeMetricKey] : 0;
      map.set(key, (map.get(key) || 0) + val);
    });
    return Array.from(map.entries()).map(([key, val]) => ({
      [activeXKey]: key,
      [activeMetricKey]: Number(val.toFixed(2)),
    }));
  }, [chartData, activeXKey, activeMetricKey]);

  // Summary statistics
  const stats = useMemo(() => {
    if (chartData.length === 0 || !activeMetricKey) return null;
    const values = chartData
      .map((r) => (typeof r[activeMetricKey] === "number" ? r[activeMetricKey] : 0))
      .filter((v) => !isNaN(v));

    if (values.length === 0) return null;
    const total = values.reduce((a, b) => a + b, 0);
    const avg = total / values.length;
    const max = Math.max(...values);
    return {
      total: total.toLocaleString(undefined, { maximumFractionDigits: 2 }),
      avg: avg.toLocaleString(undefined, { maximumFractionDigits: 2 }),
      max: max.toLocaleString(undefined, { maximumFractionDigits: 2 }),
      count: chartData.length,
    };
  }, [chartData, activeMetricKey]);

  // Filtered rows for table
  const filteredRows = useMemo(() => {
    if (!search) return chartData;
    const q = search.toLowerCase();
    return chartData.filter((row) =>
      Object.values(row).some((val) => String(val).toLowerCase().includes(q))
    );
  }, [chartData, search]);

  function copySql() {
    if (!data.sql_used) return;
    navigator.clipboard.writeText(data.sql_used);
    setCopiedSql(true);
    setTimeout(() => setCopiedSql(false), 2000);
  }

  function exportCsv() {
    if (columns.length === 0 || rawRows.length === 0) return;
    const header = columns.join(",");
    const rowsCsv = rawRows.map((r) => r.map((c) => `"${String(c ?? "").replace(/"/g, '""')}"`).join(","));
    const csvContent = "data:text/csv;charset=utf-8," + [header, ...rowsCsv].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `analytics_export_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  if (columns.length === 0 || rawRows.length === 0) {
    return (
      <div className="rounded-xl border border-border bg-surface-card p-6 text-center text-xs text-slate-400">
        No tabular data available for this query.
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-border bg-surface-card p-5 shadow-sm space-y-5">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/80 pb-3.5">
        <div>
          <h3 className="text-sm font-semibold text-white">
            {title}
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            {chartData.length} records · SQL query analysis
          </p>
        </div>

        {/* View Switcher */}
        <div className="flex items-center gap-1 rounded-lg bg-surface-muted p-1 border border-border">
          <button
            onClick={() => setViewType("bar")}
            className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition ${
              viewType === "bar"
                ? "bg-blue-600 text-white"
                : "text-slate-400 hover:text-slate-200"
            }`}
            title="Bar Chart"
          >
            <IconChartBar className="w-3.5 h-3.5" />
            <span>Bar</span>
          </button>
          <button
            onClick={() => setViewType("line")}
            className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition ${
              viewType === "line"
                ? "bg-blue-600 text-white"
                : "text-slate-400 hover:text-slate-200"
            }`}
            title="Trend Chart"
          >
            <IconChartLine className="w-3.5 h-3.5" />
            <span>Trend</span>
          </button>
          <button
            onClick={() => setViewType("area")}
            className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition ${
              viewType === "area"
                ? "bg-blue-600 text-white"
                : "text-slate-400 hover:text-slate-200"
            }`}
            title="Area Chart"
          >
            <IconChartBar className="w-3.5 h-3.5" />
            <span>Area</span>
          </button>
          <button
            onClick={() => setViewType("pie")}
            className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition ${
              viewType === "pie"
                ? "bg-blue-600 text-white"
                : "text-slate-400 hover:text-slate-200"
            }`}
            title="Breakdown"
          >
            <IconChartPie className="w-3.5 h-3.5" />
            <span>Share</span>
          </button>
          <button
            onClick={() => setViewType("table")}
            className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition ${
              viewType === "table"
                ? "bg-blue-600 text-white"
                : "text-slate-400 hover:text-slate-200"
            }`}
            title="Table View"
          >
            <IconTable className="w-3.5 h-3.5" />
            <span>Table</span>
          </button>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          {data.sql_used && (
            <button
              onClick={() => setShowSql(!showSql)}
              className={`flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs font-medium transition ${
                showSql
                  ? "border-blue-500 bg-blue-500/10 text-blue-400"
                  : "border-border bg-surface-muted text-slate-300 hover:bg-surface"
              }`}
            >
              <IconCode className="w-3.5 h-3.5" />
              SQL
            </button>
          )}
          <button
            onClick={exportCsv}
            className="flex items-center gap-1.5 rounded-md border border-border bg-surface-muted px-2.5 py-1 text-xs font-medium text-slate-300 hover:text-white transition"
          >
            <IconDownload className="w-3.5 h-3.5" />
            CSV
          </button>
        </div>
      </div>

      {/* SQL Drawer */}
      {showSql && data.sql_used && (
        <div className="rounded-lg border border-border bg-surface-muted p-3.5 relative">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
              PostgreSQL Query
            </span>
            <button
              onClick={copySql}
              className="flex items-center gap-1 text-[11px] text-slate-300 hover:text-white bg-surface px-2 py-0.5 rounded border border-border"
            >
              {copiedSql ? (
                <>
                  <IconCheck className="w-3 h-3 text-emerald-400" /> Copied
                </>
              ) : (
                <>
                  <IconCopy className="w-3 h-3" /> Copy
                </>
              )}
            </button>
          </div>
          <pre className="overflow-x-auto text-xs font-mono text-slate-300 whitespace-pre-wrap">
            {data.sql_used}
          </pre>
        </div>
      )}

      {/* Metrics Summary Cards */}
      {stats && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div className="rounded-lg border border-border bg-surface-muted/60 p-3">
            <p className="text-[11px] font-medium text-slate-400">Total {activeMetricKey}</p>
            <p className="mt-1 text-base font-bold text-white">{stats.total}</p>
          </div>
          <div className="rounded-lg border border-border bg-surface-muted/60 p-3">
            <p className="text-[11px] font-medium text-slate-400">Average</p>
            <p className="mt-1 text-base font-bold text-blue-400">{stats.avg}</p>
          </div>
          <div className="rounded-lg border border-border bg-surface-muted/60 p-3">
            <p className="text-[11px] font-medium text-slate-400">Peak Value</p>
            <p className="mt-1 text-base font-bold text-emerald-400">{stats.max}</p>
          </div>
          <div className="rounded-lg border border-border bg-surface-muted/60 p-3">
            <p className="text-[11px] font-medium text-slate-400">Record Count</p>
            <p className="mt-1 text-base font-bold text-slate-300">{stats.count}</p>
          </div>
        </div>
      )}

      {/* Axis Controls */}
      {viewType !== "table" && (
        <div className="flex flex-wrap items-center gap-4 text-xs text-slate-400 bg-surface-muted/50 p-2 rounded-lg border border-border">
          <div className="flex items-center gap-2">
            <span className="text-slate-300">Dimension (X):</span>
            <select
              value={activeXKey}
              onChange={(e) => setXAxisKey(e.target.value)}
              className="rounded border border-border bg-surface px-2 py-0.5 text-xs text-white focus:outline-none"
            >
              {columns.map((col) => (
                <option key={col} value={col}>
                  {col}
                </option>
              ))}
            </select>
          </div>

          {numericCols.length > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-slate-300">Metric (Y):</span>
              <select
                value={activeMetricKey}
                onChange={(e) => setMetricKey(e.target.value)}
                className="rounded border border-border bg-surface px-2 py-0.5 text-xs text-white focus:outline-none"
              >
                {numericCols.map((col) => (
                  <option key={col} value={col}>
                    {col}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
      )}

      {/* Chart Canvas */}
      <div className="min-h-[320px] w-full">
        {viewType === "bar" && (
          <div className="h-[320px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={aggregatedChartData} margin={{ top: 10, right: 15, left: 0, bottom: 25 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f293d" vertical={false} />
                <XAxis
                  dataKey={activeXKey}
                  stroke="#94a3b8"
                  fontSize={11}
                  tickLine={false}
                  angle={-10}
                  textAnchor="end"
                />
                <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#111827",
                    borderColor: "#1f293d",
                    borderRadius: "6px",
                    color: "#f3f4f6",
                    fontSize: "12px",
                  }}
                  cursor={{ fill: "rgba(59, 130, 246, 0.08)" }}
                />
                <Bar
                  dataKey={activeMetricKey}
                  fill="#3b82f6"
                  radius={[4, 4, 0, 0]}
                  name={activeMetricKey}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {viewType === "line" && (
          <div className="h-[320px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={aggregatedChartData} margin={{ top: 10, right: 15, left: 0, bottom: 25 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f293d" vertical={false} />
                <XAxis
                  dataKey={activeXKey}
                  stroke="#94a3b8"
                  fontSize={11}
                  tickLine={false}
                  angle={-10}
                  textAnchor="end"
                />
                <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#111827",
                    borderColor: "#1f293d",
                    borderRadius: "6px",
                    color: "#f3f4f6",
                    fontSize: "12px",
                  }}
                />
                <Line
                  type="monotone"
                  dataKey={activeMetricKey}
                  stroke="#10b981"
                  strokeWidth={2.5}
                  dot={{ r: 3.5, fill: "#10b981" }}
                  activeDot={{ r: 5.5, fill: "#10b981", stroke: "#fff" }}
                  name={activeMetricKey}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}

        {viewType === "area" && (
          <div className="h-[320px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={aggregatedChartData} margin={{ top: 10, right: 15, left: 0, bottom: 25 }}>
                <defs>
                  <linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.4} />
                    <stop offset="100%" stopColor="#3b82f6" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f293d" vertical={false} />
                <XAxis
                  dataKey={activeXKey}
                  stroke="#94a3b8"
                  fontSize={11}
                  tickLine={false}
                  angle={-10}
                  textAnchor="end"
                />
                <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#111827",
                    borderColor: "#1f293d",
                    borderRadius: "6px",
                    color: "#f3f4f6",
                    fontSize: "12px",
                  }}
                />
                <Area
                  type="monotone"
                  dataKey={activeMetricKey}
                  stroke="#3b82f6"
                  strokeWidth={2}
                  fill="url(#areaGradient)"
                  name={activeMetricKey}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}

        {viewType === "pie" && (
          <div className="h-[320px] w-full flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#111827",
                    borderColor: "#1f293d",
                    borderRadius: "6px",
                    color: "#f3f4f6",
                    fontSize: "12px",
                  }}
                />
                <Legend
                  verticalAlign="bottom"
                  height={32}
                  formatter={(val) => <span className="text-xs text-slate-300">{val}</span>}
                />
                <Pie
                  data={aggregatedChartData}
                  dataKey={activeMetricKey}
                  nameKey={activeXKey}
                  cx="50%"
                  cy="45%"
                  outerRadius={95}
                  innerRadius={50}
                  paddingAngle={2}
                >
                  {aggregatedChartData.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={PALETTE[index % PALETTE.length]} />
                  ))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
          </div>
        )}

        {viewType === "table" && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Filter table..."
                className="w-56 rounded-md border border-border bg-surface px-2.5 py-1 text-xs text-white placeholder-slate-500 focus:outline-none"
              />
              <span className="text-xs text-slate-400">
                {filteredRows.length} rows
              </span>
            </div>
            <div className="overflow-x-auto rounded-lg border border-border max-h-[380px]">
              <table className="w-full text-left text-xs">
                <thead className="sticky top-0 bg-surface-muted text-slate-400 font-semibold border-b border-border">
                  <tr>
                    {columns.map((col) => (
                      <th key={col} className="px-3.5 py-2.5 uppercase tracking-wider">
                        {col}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60">
                  {filteredRows.map((row, rIdx) => (
                    <tr key={rIdx} className="hover:bg-surface-muted/50 transition">
                      {columns.map((col) => {
                        const cellVal = row[col];
                        const isNum = typeof cellVal === "number";
                        return (
                          <td
                            key={col}
                            className={`px-3.5 py-2 ${
                              isNum ? "font-mono text-blue-300" : "text-slate-200"
                            }`}
                          >
                            {isNum ? cellVal.toLocaleString() : String(cellVal ?? "—")}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
