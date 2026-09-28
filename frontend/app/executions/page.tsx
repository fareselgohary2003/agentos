"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import AppShell from "@/components/AppShell";
import { api } from "@/lib/api";
import { IconExecutions, IconPlay } from "@/components/Icons";

const STATUS_CONFIG: Record<string, { label: string; badge: string }> = {
  done: { label: "Completed", badge: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30" },
  completed: { label: "Completed", badge: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30" },
  executing: { label: "Executing", badge: "bg-amber-500/10 text-amber-400 border-amber-500/30 animate-pulse" },
  verifying: { label: "Verifying", badge: "bg-indigo-500/10 text-indigo-400 border-indigo-500/30" },
  queued: { label: "Queued", badge: "bg-slate-500/10 text-slate-400 border-slate-500/30" },
  failed: { label: "Failed", badge: "bg-rose-500/10 text-rose-400 border-rose-500/30" },
  rejected: { label: "Rejected", badge: "bg-rose-500/10 text-rose-400 border-rose-500/30" },
  awaiting_approval: { label: "Approval Required", badge: "bg-purple-500/10 text-purple-400 border-purple-500/30" },
};

export default function ExecutionsPage() {
  const [executions, setExecutions] = useState<any[]>([]);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  useEffect(() => {
    const load = () => api.listExecutions().then(setExecutions).catch(() => {});
    load();
    const interval = setInterval(load, 3000);
    return () => clearInterval(interval);
  }, []);

  const filtered = executions.filter((e) => {
    const matchesSearch = !search || e.goal?.toLowerCase().includes(search.toLowerCase()) || e.id.includes(search);
    const matchesStatus = statusFilter === "all" || e.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <AppShell>
      <div className="space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
              <IconExecutions className="w-6 h-6 text-indigo-400" />
              Executions History
            </h1>
            <p className="text-xs text-slate-400 mt-1">
              Real-time feed of multi-agent plans, task runs, and data outputs
            </p>
          </div>
          <Link
            href="/workflows"
            className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 px-4 py-2 text-xs font-semibold text-white shadow-lg shadow-indigo-500/25 transition hover:scale-[1.02]"
          >
            <IconPlay className="w-3.5 h-3.5" />
            <span>New Execution</span>
          </Link>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center justify-between gap-3 bg-surface-card p-3 rounded-2xl border border-border/80">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by goal or ID..."
            className="w-72 rounded-xl border border-border bg-surface px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />

          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400">Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="rounded-xl border border-border bg-surface px-3 py-1.5 text-xs text-white focus:outline-none focus:border-indigo-500"
            >
              <option value="all">All Statuses</option>
              <option value="done">Completed</option>
              <option value="executing">Executing</option>
              <option value="failed">Failed</option>
              <option value="queued">Queued</option>
            </select>
          </div>
        </div>

        {/* Executions Table */}
        <div className="overflow-hidden rounded-2xl border border-border/80 bg-surface-card shadow-xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-surface-muted text-slate-400 font-semibold border-b border-border/60">
                <tr>
                  <th className="px-5 py-3.5 uppercase tracking-wider">Goal & Objective</th>
                  <th className="px-5 py-3.5 uppercase tracking-wider">Status</th>
                  <th className="px-5 py-3.5 uppercase tracking-wider">Tasks</th>
                  <th className="px-5 py-3.5 uppercase tracking-wider">Started</th>
                  <th className="px-5 py-3.5 uppercase tracking-wider text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/40">
                {filtered.map((e) => {
                  const statusInfo = STATUS_CONFIG[e.status] ?? STATUS_CONFIG.queued;
                  return (
                    <tr key={e.id} className="hover:bg-surface-muted/50 transition">
                      <td className="px-5 py-4 max-w-md">
                        <Link
                          href={`/executions/${e.id}`}
                          className="font-semibold text-slate-200 hover:text-indigo-400 line-clamp-1 transition"
                        >
                          {e.goal}
                        </Link>
                        <p className="text-[10px] text-slate-500 font-mono mt-0.5">{e.id}</p>
                      </td>
                      <td className="px-5 py-4">
                        <span
                          className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[10px] font-semibold ${statusInfo.badge}`}
                        >
                          {statusInfo.label}
                        </span>
                      </td>
                      <td className="px-5 py-4 text-slate-300">
                        {e.tasks?.length ?? 0} tasks
                      </td>
                      <td className="px-5 py-4 text-slate-400">
                        {e.started_at ? new Date(e.started_at).toLocaleString() : "—"}
                      </td>
                      <td className="px-5 py-4 text-right">
                        <Link
                          href={`/executions/${e.id}`}
                          className="inline-flex items-center rounded-lg border border-border bg-surface-muted px-3 py-1 text-xs font-medium text-slate-300 hover:border-indigo-500 hover:text-white transition"
                        >
                          Inspect →
                        </Link>
                      </td>
                    </tr>
                  );
                })}
                {filtered.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-5 py-12 text-center text-slate-500">
                      No matching executions found.
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
