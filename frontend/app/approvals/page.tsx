"use client";

import React, { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { api } from "@/lib/api";
import { IconApprovals, IconCheck } from "@/components/Icons";

export default function ApprovalsPage() {
  const [approvals, setApprovals] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);

  function load() {
    api.listApprovals().then(setApprovals).catch((e) => setError(e.message));
  }

  useEffect(load, []);

  async function decide(id: string, approve: boolean) {
    try {
      await (approve ? api.approveApproval(id) : api.rejectApproval(id));
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to record decision");
    }
  }

  return (
    <AppShell>
      <div className="space-y-6 max-w-4xl mx-auto">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
            <IconApprovals className="w-6 h-6 text-indigo-400" />
            Human-in-the-Loop Approvals
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Safety gates for sensitive tool calls, external side-effects, and production system actions
          </p>
        </div>

        {error && <p className="text-xs text-rose-400">{error}</p>}

        <div className="space-y-4">
          {approvals.map((a) => (
            <div
              key={a.id}
              className="rounded-2xl border border-amber-500/30 bg-surface-card p-6 shadow-xl space-y-4"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="flex h-2.5 w-2.5 rounded-full bg-amber-400 animate-ping" />
                  <h3 className="text-sm font-bold text-white">
                    {a.requested_by_agent || "Agent"} requested: <span className="font-mono text-indigo-300">{a.action}</span>
                  </h3>
                </div>
                <span className="rounded-full border border-rose-500/40 bg-rose-500/10 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-rose-400">
                  {a.risk_level || "high"} risk
                </span>
              </div>

              <div className="space-y-1">
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                  Action Payload:
                </span>
                <pre className="overflow-x-auto rounded-xl border border-border/60 bg-surface-muted p-4 text-xs font-mono text-slate-200">
                  {JSON.stringify(a.payload, null, 2)}
                </pre>
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  onClick={() => decide(a.id, false)}
                  className="rounded-xl border border-border/80 bg-surface-muted px-4 py-2 text-xs font-semibold text-slate-300 hover:border-rose-500/50 hover:text-rose-300 transition"
                >
                  Reject Action
                </button>
                <button
                  onClick={() => decide(a.id, true)}
                  className="rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 px-5 py-2 text-xs font-semibold text-white shadow-lg shadow-emerald-500/20 hover:scale-[1.02] transition"
                >
                  Approve Execution
                </button>
              </div>
            </div>
          ))}

          {approvals.length === 0 && (
            <div className="rounded-2xl border border-dashed border-border p-12 text-center text-xs text-slate-500 space-y-2">
              <IconCheck className="w-8 h-8 text-emerald-400 mx-auto opacity-75" />
              <p className="font-semibold text-slate-300">All clear — No pending approvals</p>
              <p>When high-risk actions occur, they will require human authorization here.</p>
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
