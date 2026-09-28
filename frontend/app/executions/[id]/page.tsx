"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import AppShell from "@/components/AppShell";
import { api } from "@/lib/api";
import DataVisualizer from "@/components/DataVisualizer";
import {
  IconSparkles,
  IconCheck,
  IconCode,
  IconAgents,
  IconExecutions,
} from "@/components/Icons";

const STATUS_CONFIG: Record<string, { label: string; badge: string; icon: string }> = {
  done: { label: "Completed", badge: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30", icon: "✓" },
  completed: { label: "Completed", badge: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30", icon: "✓" },
  executing: { label: "Executing", badge: "bg-amber-500/10 text-amber-400 border-amber-500/30 animate-pulse", icon: "●" },
  verifying: { label: "Verifying Plan", badge: "bg-indigo-500/10 text-indigo-400 border-indigo-500/30 animate-pulse", icon: "⟳" },
  replanning: { label: "Replanning", badge: "bg-purple-500/10 text-purple-400 border-purple-500/30", icon: "⟳" },
  queued: { label: "Queued", badge: "bg-slate-500/10 text-slate-400 border-slate-500/30", icon: "○" },
  failed: { label: "Failed", badge: "bg-rose-500/10 text-rose-400 border-rose-500/30", icon: "✗" },
  rejected: { label: "Rejected", badge: "bg-rose-500/10 text-rose-400 border-rose-500/30", icon: "✗" },
  awaiting_approval: { label: "Needs Approval", badge: "bg-purple-500/10 text-purple-400 border-purple-500/30", icon: "!" },
};

export default function ExecutionDetailPage({ params }: { params: { id: string } }) {
  const [execution, setExecution] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = () =>
      api.getExecution(params.id).then(setExecution).catch((e) => setError(e.message));
    load();
    const interval = setInterval(() => {
      if (execution && !["queued", "executing", "verifying", "replanning"].includes(execution.status)) {
        return;
      }
      load();
    }, 2500);
    return () => clearInterval(interval);
  }, [params.id, execution?.status]);

  if (error) {
    return (
      <AppShell>
        <div className="rounded-2xl border border-rose-500/30 bg-rose-950/20 p-6 text-rose-300">
          <p className="font-semibold">Error Loading Execution</p>
          <p className="text-xs mt-1">{error}</p>
        </div>
      </AppShell>
    );
  }

  if (!execution) {
    return (
      <AppShell>
        <div className="flex flex-col items-center justify-center py-24 space-y-4">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-indigo-500 border-t-transparent" />
          <p className="text-sm text-slate-400">Loading multi-agent execution telemetry...</p>
        </div>
      </AppShell>
    );
  }

  const statusInfo = STATUS_CONFIG[execution.status] ?? STATUS_CONFIG.queued;
  const isRunning = ["queued", "executing", "verifying", "replanning"].includes(execution.status);

  return (
    <AppShell>
      <div className="space-y-8 max-w-5xl mx-auto">
        {/* Execution Header Banner */}
        <div className="rounded-3xl border border-border/80 bg-surface-card p-6 md:p-8 shadow-2xl space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <Link
                href="/executions"
                className="text-xs font-semibold text-slate-400 hover:text-white transition flex items-center gap-1"
              >
                ← Executions
              </Link>
              <span className="text-slate-600">/</span>
              <span className="font-mono text-xs text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded-md border border-indigo-500/20">
                {execution.id}
              </span>
            </div>

            <div className="flex items-center gap-2">
              <span
                className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold ${statusInfo.badge}`}
              >
                <span>{statusInfo.icon}</span>
                <span>{statusInfo.label}</span>
              </span>
            </div>
          </div>

          <div>
            <h1 className="text-xl md:text-2xl font-bold text-white tracking-tight">
              {execution.goal}
            </h1>
            <div className="flex flex-wrap items-center gap-4 text-xs text-slate-400 mt-2">
              <span>
                Started: {execution.started_at ? new Date(execution.started_at).toLocaleString() : "—"}
              </span>
              <span>•</span>
              <span>Tasks Planned: {execution.tasks?.length ?? 0}</span>
              {isRunning && (
                <>
                  <span>•</span>
                  <span className="text-amber-400 flex items-center gap-1">
                    <span className="h-2 w-2 rounded-full bg-amber-400 animate-ping" />
                    Agent orchestrator active...
                  </span>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Final Synthesized Report (if completed) */}
        {execution.plan?.final_output && (
          <div className="rounded-3xl border border-emerald-500/30 bg-gradient-to-b from-emerald-950/20 via-surface-card to-surface-card p-6 md:p-8 shadow-2xl space-y-4">
            <div className="flex items-center gap-2 text-emerald-400">
              <IconSparkles className="w-5 h-5" />
              <h2 className="text-lg font-bold text-white">Executive Synthesis & Final Report</h2>
            </div>
            <div className="prose prose-invert max-w-none text-sm leading-relaxed text-slate-200 whitespace-pre-wrap rounded-2xl bg-surface-muted/60 p-5 border border-border/60">
              {typeof execution.plan.final_output === "string"
                ? execution.plan.final_output
                : execution.plan.final_output.summary || JSON.stringify(execution.plan.final_output, null, 2)}
            </div>
          </div>
        )}

        {/* Multi-Agent Tasks Execution Timeline */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <IconAgents className="w-4 h-4 text-indigo-400" />
              Task Execution Pipeline
            </h2>
            <span className="text-xs text-slate-400">
              {execution.tasks?.filter((t: any) => (t.executions?.[0]?.status ?? t.status) === "done").length ?? 0}{" "}
              of {execution.tasks?.length ?? 0} completed
            </span>
          </div>

          <div className="space-y-6">
            {(execution.tasks ?? []).map((task: any, index: number) => {
              const exec = task.executions?.[0];
              const taskStatus = exec?.status ?? task.status ?? "pending";
              const taskStatusConfig = STATUS_CONFIG[taskStatus] ?? STATUS_CONFIG.queued;
              const output = exec?.output;
              const hasTabularData =
                output &&
                ((output.columns && output.rows) ||
                  (Array.isArray(output) && output.length > 0 && typeof output[0] === "object"));

              return (
                <div
                  key={task.id || index}
                  className="rounded-2xl border border-border/80 bg-surface-card p-6 shadow-xl transition space-y-4"
                >
                  {/* Task Header */}
                  <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/60 pb-3">
                    <div className="flex items-center gap-2.5">
                      <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-500/10 text-xs font-bold text-indigo-400 border border-indigo-500/20">
                        {index + 1}
                      </div>
                      <div>
                        <span className="text-xs font-bold text-white uppercase tracking-wider">
                          {task.agent || "Agent"}
                        </span>
                        <span className="text-xs text-slate-500 font-mono ml-2">({task.id})</span>
                      </div>
                    </div>

                    <span
                      className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${taskStatusConfig.badge}`}
                    >
                      <span>{taskStatusConfig.icon}</span>
                      <span>{taskStatusConfig.label}</span>
                    </span>
                  </div>

                  {/* Task Description */}
                  <p className="text-sm font-medium text-slate-300">{task.description}</p>

                  {/* If Data Agent with Tabular Data -> Render High-End DataVisualizer */}
                  {hasTabularData && (
                    <div className="pt-2">
                      <DataVisualizer
                        data={output}
                        title={`Data Agent Results: ${task.description.slice(0, 60)}...`}
                      />
                    </div>
                  )}

                  {/* If Research Agent or structured results */}
                  {output && !hasTabularData && (
                    <div className="space-y-2 pt-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                          Agent Output & Telemetry
                        </span>
                      </div>
                      <div className="rounded-xl border border-border/60 bg-surface-muted p-4">
                        {output.results && Array.isArray(output.results) ? (
                          <div className="space-y-3">
                            {output.results.map((res: any, rIdx: number) => (
                              <div key={rIdx} className="rounded-lg bg-surface-card p-3 border border-border/40">
                                <p className="text-xs font-bold text-indigo-300">{res.title || "Finding"}</p>
                                <p className="text-xs text-slate-300 mt-1">{res.snippet || res.content || JSON.stringify(res)}</p>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <pre className="overflow-x-auto text-xs font-mono text-slate-200 whitespace-pre-wrap">
                            {typeof output === "string" ? output : JSON.stringify(output, null, 2)}
                          </pre>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Error display if failed */}
                  {exec?.error && (
                    <div className="rounded-xl border border-rose-500/30 bg-rose-950/20 p-4 text-xs text-rose-300">
                      <p className="font-semibold">Task Error:</p>
                      <p className="mt-0.5">{exec.error}</p>
                    </div>
                  )}
                </div>
              );
            })}

            {(!execution.tasks || execution.tasks.length === 0) && (
              <div className="rounded-2xl border border-dashed border-border/80 p-8 text-center text-sm text-slate-400">
                Supervisor is analyzing goal requirements and building execution DAG...
              </div>
            )}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
