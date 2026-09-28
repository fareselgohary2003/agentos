"use client";

import React, { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { api } from "@/lib/api";
import { IconMonitoring, IconSparkles } from "@/components/Icons";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";

const PALETTE = ["#6366f1", "#a855f7", "#38bdf8", "#34d399", "#fbbf24", "#f43f5e"];

export default function MonitoringPage() {
  const [summary, setSummary] = useState<any>(null);
  const [costByModel, setCostByModel] = useState<any[]>([]);

  useEffect(() => {
    api.monitoringSummary().then(setSummary).catch(() => {});
    api.costByModel().then(setCostByModel).catch(() => {});
  }, []);

  return (
    <AppShell>
      <div className="space-y-8">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
            <IconMonitoring className="w-6 h-6 text-indigo-400" />
            Monitoring & Cost Analytics
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Real-time multi-model LLM telemetry, latency tracking, and operational cost accounting
          </p>
        </div>

        {/* Telemetry Metrics */}
        {summary && (
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <div className="rounded-2xl border border-indigo-500/20 bg-surface-card p-5 shadow-lg">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                Total Executions
              </span>
              <p className="mt-2 text-2xl font-black text-white">{summary.total_executions}</p>
              <p className="mt-1 text-[10px] text-slate-400">All agent workflow runs</p>
            </div>
            <div className="rounded-2xl border border-emerald-500/20 bg-surface-card p-5 shadow-lg">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                Success Rate
              </span>
              <p className="mt-2 text-2xl font-black text-emerald-400">
                {summary.success_rate != null ? `${(summary.success_rate * 100).toFixed(0)}%` : "100%"}
              </p>
              <p className="mt-1 text-[10px] text-slate-400">Plan verification rate</p>
            </div>
            <div className="rounded-2xl border border-sky-500/20 bg-surface-card p-5 shadow-lg">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                Avg Latency (24h)
              </span>
              <p className="mt-2 text-2xl font-black text-sky-400">
                {summary.avg_latency_ms_24h || 0} ms
              </p>
              <p className="mt-1 text-[10px] text-slate-400">End-to-end task turnaround</p>
            </div>
            <div className="rounded-2xl border border-purple-500/20 bg-surface-card p-5 shadow-lg">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                Est. Cost (24h)
              </span>
              <p className="mt-2 text-2xl font-black text-purple-400">
                ${(summary.estimated_cost_24h_usd || 0).toFixed(4)}
              </p>
              <p className="mt-1 text-[10px] text-slate-400">Aggregated provider spend</p>
            </div>
          </div>
        )}

        {/* Visual Charts: Cost and Token Allocation */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Tokens by Model Bar Chart */}
          <div className="rounded-2xl border border-border/80 bg-surface-card p-6 shadow-xl space-y-4">
            <h2 className="text-sm font-bold text-white">Token Usage by Model</h2>
            <div className="h-[260px] w-full">
              {costByModel.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={costByModel} margin={{ top: 10, right: 10, left: 0, bottom: 25 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                    <XAxis dataKey="model" stroke="#94a3b8" fontSize={11} tickLine={false} />
                    <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#0f172a",
                        borderColor: "#334155",
                        borderRadius: "8px",
                        color: "#f8fafc",
                        fontSize: "12px",
                      }}
                    />
                    <Bar dataKey="tokens" fill="#6366f1" radius={[6, 6, 0, 0]} name="Tokens" />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex h-full items-center justify-center text-xs text-slate-500">
                  No model usage data recorded.
                </div>
              )}
            </div>
          </div>

          {/* Model Share Pie Chart */}
          <div className="rounded-2xl border border-border/80 bg-surface-card p-6 shadow-xl space-y-4">
            <h2 className="text-sm font-bold text-white">Token Share Distribution</h2>
            <div className="h-[260px] w-full flex items-center justify-center">
              {costByModel.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#0f172a",
                        borderColor: "#334155",
                        borderRadius: "8px",
                        color: "#f8fafc",
                        fontSize: "12px",
                      }}
                    />
                    <Legend
                      verticalAlign="bottom"
                      height={36}
                      formatter={(val) => <span className="text-xs text-slate-300">{val}</span>}
                    />
                    <Pie
                      data={costByModel}
                      dataKey="tokens"
                      nameKey="model"
                      cx="50%"
                      cy="45%"
                      outerRadius={85}
                      innerRadius={45}
                      paddingAngle={3}
                    >
                      {costByModel.map((_, index) => (
                        <Cell key={`cell-${index}`} fill={PALETTE[index % PALETTE.length]} />
                      ))}
                    </Pie>
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex h-full items-center justify-center text-xs text-slate-500">
                  No model usage data recorded.
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Cost Table */}
        <div className="rounded-2xl border border-border/80 bg-surface-card shadow-xl overflow-hidden">
          <div className="p-5 border-b border-border/60">
            <h2 className="text-sm font-bold text-white">Detailed Model Accounting</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-surface-muted text-slate-400 font-semibold border-b border-border/60">
                <tr>
                  <th className="px-5 py-3.5 uppercase tracking-wider">Provider</th>
                  <th className="px-5 py-3.5 uppercase tracking-wider">Model</th>
                  <th className="px-5 py-3.5 uppercase tracking-wider">Tokens Processed</th>
                  <th className="px-5 py-3.5 uppercase tracking-wider">Cost (USD)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/40">
                {costByModel.map((row, i) => (
                  <tr key={i} className="hover:bg-surface-muted/50 transition">
                    <td className="px-5 py-3.5 font-semibold text-slate-200 uppercase">{row.provider}</td>
                    <td className="px-5 py-3.5 font-mono text-indigo-300">{row.model}</td>
                    <td className="px-5 py-3.5 text-slate-300">{row.tokens.toLocaleString()}</td>
                    <td className="px-5 py-3.5 font-semibold text-emerald-400">${row.cost_usd}</td>
                  </tr>
                ))}
                {costByModel.length === 0 && (
                  <tr>
                    <td colSpan={4} className="px-5 py-10 text-center text-slate-500">
                      No usage recorded yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
