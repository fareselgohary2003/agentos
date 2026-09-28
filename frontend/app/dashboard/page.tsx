"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import AppShell from "@/components/AppShell";
import { api } from "@/lib/api";
import DataVisualizer from "@/components/DataVisualizer";
import {
  IconPlay,
  IconExecutions,
  IconAgents,
  IconWorkflows,
  IconMonitoring,
  IconChartBar,
} from "@/components/Icons";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";

const DEMO_PREVIEW_DATA = {
  columns: ["category", "region", "quarter", "revenue"],
  rows: [
    ["Lighting", "North America - East", "2026-Q1", 142500],
    ["Textiles", "North America - East", "2026-Q1", 98200],
    ["Kitchenware", "North America - West", "2026-Q1", 115400],
    ["Decor", "Europe", "2026-Q1", 87600],
    ["Furniture", "APAC", "2026-Q1", 210000],
    ["Lighting", "Europe", "2026-Q2", 168000],
    ["Furniture", "North America - East", "2026-Q2", 245000],
    ["Kitchenware", "APAC", "2026-Q2", 132000],
    ["Textiles", "Europe", "2026-Q2", 104500],
    ["Decor", "North America - West", "2026-Q2", 92000],
  ],
  row_count: 10,
  sql_used: `SELECT pc.name AS category, r.name AS region, so.quarter, SUM(so.total_amount) AS revenue
FROM sales_orders so
JOIN products p ON p.id = so.product_id
JOIN product_categories pc ON pc.id = p.category_id
JOIN regions r ON r.id = so.region_id
GROUP BY pc.name, r.name, so.quarter
ORDER BY revenue DESC;`,
};

const SAMPLE_PROMPTS = [
  "Analyze Q1 vs Q2 sales revenue by product category and region",
  "Compare retail vs wholesale segment order volume and margins",
  "Investigate Lighting sales performance in North America - East",
];

const STATUS_BADGE: Record<string, { bg: string; text: string; label: string }> = {
  done: { bg: "bg-emerald-500/10 border-emerald-500/30", text: "text-emerald-400", label: "Completed" },
  completed: { bg: "bg-emerald-500/10 border-emerald-500/30", text: "text-emerald-400", label: "Completed" },
  executing: { bg: "bg-amber-500/10 border-amber-500/30", text: "text-amber-400", label: "Running" },
  queued: { bg: "bg-slate-500/10 border-slate-500/30", text: "text-slate-400", label: "Queued" },
  failed: { bg: "bg-rose-500/10 border-rose-500/30", text: "text-rose-400", label: "Failed" },
  rejected: { bg: "bg-rose-500/10 border-rose-500/30", text: "text-rose-400", label: "Rejected" },
  awaiting_approval: { bg: "bg-purple-500/10 border-purple-500/30", text: "text-purple-400", label: "Pending Approval" },
};

export default function DashboardPage() {
  const router = useRouter();
  const [summary, setSummary] = useState<any>(null);
  const [costByModel, setCostByModel] = useState<any[]>([]);
  const [executions, setExecutions] = useState<any[]>([]);
  const [goal, setGoal] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.monitoringSummary().then(setSummary).catch((e) => setError(e.message));
    api.costByModel().then(setCostByModel).catch(() => {});
    api.listExecutions().then((list) => setExecutions(list.slice(0, 5))).catch(() => {});
  }, []);

  async function handleLaunchGoal(e: React.FormEvent) {
    e.preventDefault();
    if (!goal.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      const { execution_id } = await api.executeGoal(goal);
      router.push(`/executions/${execution_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to run analysis");
      setSubmitting(false);
    }
  }

  const kpis = summary
    ? [
        {
          label: "Active Agents",
          value: summary.active_agents,
          sub: "Available in fleet",
          icon: IconAgents,
          color: "text-blue-400",
        },
        {
          label: "Running Workflows",
          value: summary.running_workflows,
          sub: "Active pipelines",
          icon: IconWorkflows,
          color: "text-purple-400",
        },
        {
          label: "Total Executions",
          value: summary.total_executions,
          sub: "Total goal runs",
          icon: IconExecutions,
          color: "text-sky-400",
        },
        {
          label: "Success Rate",
          value: summary.success_rate != null ? `${(summary.success_rate * 100).toFixed(0)}%` : "100%",
          sub: "Verification passing",
          icon: IconChartBar,
          color: "text-emerald-400",
        },
        {
          label: "Tokens (24h)",
          value: (summary.tokens_24h || 0).toLocaleString(),
          sub: "Model consumption",
          icon: IconMonitoring,
          color: "text-amber-400",
        },
        {
          label: "Est. Spend (24h)",
          value: `$${(summary.estimated_cost_24h_usd || 0).toFixed(4)}`,
          sub: "Provider billing",
          icon: IconChartBar,
          color: "text-rose-400",
        },
      ]
    : [];

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Goal Launch Console */}
        <div className="rounded-xl border border-border bg-surface-card p-6 shadow-sm space-y-3">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-white">
              Data & Strategic Analysis Console
            </h1>
            <p className="text-xs text-slate-400 mt-0.5">
              Submit business goals to automatically query databases, analyze market signals, and generate executive summaries.
            </p>
          </div>

          <form onSubmit={handleLaunchGoal} className="space-y-3 pt-1">
            <div className="relative flex items-center">
              <input
                type="text"
                required
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
                placeholder="e.g. Analyze sales performance by product category and region, and highlight key trends..."
                className="w-full rounded-lg border border-border bg-surface px-3.5 py-2.5 pr-32 text-xs text-white placeholder-slate-500 outline-none transition focus:border-blue-500"
              />
              <button
                type="submit"
                disabled={submitting || !goal.trim()}
                className="absolute right-1.5 flex items-center gap-1.5 rounded-md bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-blue-500 disabled:opacity-50 transition"
              >
                <IconPlay className="w-3 h-3" />
                <span>{submitting ? "Analyzing..." : "Run Analysis"}</span>
              </button>
            </div>

            {error && <p className="text-xs text-rose-400">{error}</p>}

            {/* Prompt pills */}
            <div className="flex flex-wrap items-center gap-2 pt-0.5">
              <span className="text-[11px] text-slate-400">Quick queries:</span>
              {SAMPLE_PROMPTS.map((prompt, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => setGoal(prompt)}
                  className="rounded-md border border-border bg-surface-muted px-2.5 py-0.5 text-[11px] text-slate-300 hover:border-blue-500 hover:text-white transition"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </form>
        </div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-2 gap-3.5 md:grid-cols-3 lg:grid-cols-6">
          {(summary ? kpis : Array(6).fill({ label: "Loading...", value: "—", sub: "...", icon: IconAgents })).map(
            (kpi, i) => {
              const Icon = kpi.icon;
              return (
                <div
                  key={i}
                  className="rounded-xl border border-border bg-surface-card p-4 transition hover:border-slate-700"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-medium text-slate-400">{kpi.label}</span>
                    <Icon className={`w-3.5 h-3.5 ${kpi.color ?? "text-slate-400"}`} />
                  </div>
                  <p className="mt-1.5 text-xl font-bold tracking-tight text-white">{kpi.value}</p>
                  <p className="mt-0.5 text-[10px] text-slate-400 truncate">{kpi.sub}</p>
                </div>
              );
            }
          )}
        </div>

        {/* Live Visualizer Section */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <div>
              <h2 className="text-sm font-bold text-white tracking-tight">
                Live Data Analysis & Visualizer
              </h2>
              <p className="text-[11px] text-slate-400">
                Interactive charts rendered directly from executed business queries
              </p>
            </div>
            <Link
              href="/executions"
              className="text-xs font-medium text-blue-400 hover:text-blue-300"
            >
              Execution History →
            </Link>
          </div>

          <DataVisualizer
            data={DEMO_PREVIEW_DATA}
            title="Revenue Performance: Category Breakdown by Region (Brightleaf)"
          />
        </div>

        {/* Two-column Section: Model Accounting & Recent Runs */}
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
          {/* Spend Breakdown */}
          <div className="rounded-xl border border-border bg-surface-card p-5 shadow-sm space-y-3">
            <div className="flex items-center justify-between border-b border-border pb-2.5">
              <div>
                <h3 className="text-xs font-bold text-white uppercase tracking-wider">Model Token Usage</h3>
                <p className="text-[11px] text-slate-400">Tokens consumed by active models</p>
              </div>
              <Link
                href="/monitoring"
                className="text-xs text-blue-400 hover:text-blue-300"
              >
                Monitoring →
              </Link>
            </div>

            {costByModel.length > 0 ? (
              <div className="h-[200px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={costByModel} margin={{ top: 10, right: 10, left: 0, bottom: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1f293d" vertical={false} />
                    <XAxis dataKey="model" stroke="#94a3b8" fontSize={10} tickLine={false} />
                    <YAxis stroke="#94a3b8" fontSize={10} tickLine={false} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#111827",
                        borderColor: "#1f293d",
                        borderRadius: "6px",
                        color: "#f3f4f6",
                        fontSize: "12px",
                      }}
                    />
                    <Bar dataKey="tokens" fill="#3b82f6" radius={[4, 4, 0, 0]} name="Tokens" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="flex h-[180px] items-center justify-center text-xs text-slate-500">
                No active token logs for this cycle.
              </div>
            )}
          </div>

          {/* Recent Executions */}
          <div className="rounded-xl border border-border bg-surface-card p-5 shadow-sm space-y-3">
            <div className="flex items-center justify-between border-b border-border pb-2.5">
              <div>
                <h3 className="text-xs font-bold text-white uppercase tracking-wider">Recent Executions</h3>
                <p className="text-[11px] text-slate-400">Latest analysis workflows</p>
              </div>
              <Link
                href="/executions"
                className="text-xs text-blue-400 hover:text-blue-300"
              >
                View all →
              </Link>
            </div>

            <div className="space-y-2">
              {executions.map((e) => {
                const badge = STATUS_BADGE[e.status] ?? STATUS_BADGE.queued;
                return (
                  <Link
                    key={e.id}
                    href={`/executions/${e.id}`}
                    className="flex items-center justify-between rounded-lg border border-border bg-surface-muted/50 p-2.5 hover:bg-surface-muted hover:border-slate-700 transition"
                  >
                    <div className="min-w-0 flex-1 pr-3">
                      <p className="truncate text-xs font-medium text-slate-200">
                        {e.goal}
                      </p>
                      <p className="text-[10px] text-slate-400 mt-0.5">
                        {e.started_at ? new Date(e.started_at).toLocaleTimeString() : "Queued"}
                      </p>
                    </div>
                    <span
                      className={`inline-flex items-center rounded border px-2 py-0.5 text-[10px] font-medium ${badge.bg} ${badge.text}`}
                    >
                      {badge.label}
                    </span>
                  </Link>
                );
              })}

              {executions.length === 0 && (
                <div className="py-8 text-center text-xs text-slate-500">
                  No previous runs. Enter a query above to start!
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
