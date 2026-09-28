"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import AppShell from "@/components/AppShell";
import { api } from "@/lib/api";
import { IconWorkflows, IconPlay, IconSparkles } from "@/components/Icons";

const QUICK_GOALS = [
  {
    title: "Executive Revenue & Margin Analysis",
    prompt: "Analyze Q1 and Q2 sales revenue by product category and region, highlight top drivers, and prepare an executive briefing.",
    badge: "Analytics",
  },
  {
    title: "Retail vs Wholesale Customer Segmentation",
    prompt: "Compare average order value and order volume between retail and wholesale customer segments across all regions.",
    badge: "Segmentation",
  },
  {
    title: "Market Competitor & AI Agent Research",
    prompt: "Research state-of-the-art enterprise AI workforce platforms and synthesize a competitive matrix with recommendations.",
    badge: "Intelligence",
  },
];

export default function WorkflowsPage() {
  const router = useRouter();
  const [workflows, setWorkflows] = useState<any[]>([]);
  const [goal, setGoal] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listWorkflows().then(setWorkflows).catch((e) => setError(e.message));
  }, []);

  async function submitGoal(e: React.FormEvent) {
    e.preventDefault();
    if (!goal.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      const { execution_id } = await api.executeGoal(goal);
      router.push(`/executions/${execution_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit goal");
      setSubmitting(false);
    }
  }

  return (
    <AppShell>
      <div className="space-y-8 max-w-5xl mx-auto">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
            <IconWorkflows className="w-6 h-6 text-indigo-400" />
            Workflows & Goal Orchestration
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Dispatch dynamic high-level business goals or trigger predefined multi-agent workflow DAGs
          </p>
        </div>

        {/* Dynamic Goal Launcher Form */}
        <div className="rounded-3xl border border-indigo-500/20 bg-gradient-to-b from-indigo-950/40 via-surface-card to-surface-card p-6 md:p-8 shadow-2xl space-y-4">
          <div className="flex items-center gap-2 text-indigo-300">
            <IconSparkles className="w-4 h-4 text-indigo-400" />
            <h2 className="text-sm font-bold uppercase tracking-wider">Dynamic Goal Dispatcher</h2>
          </div>
          <p className="text-xs text-slate-400">
            Enter any natural language business goal. The Supervisor agent will inspect tenant databases, generate SQL, execute research, and produce visualized reports.
          </p>

          <form onSubmit={submitGoal} className="space-y-4 pt-2">
            <textarea
              required
              rows={3}
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              placeholder="e.g. Analyze our Q2 sales decline, break down revenue by product category and region, and prepare an executive summary report..."
              className="w-full rounded-2xl border border-slate-700 bg-surface/90 p-4 text-sm text-white placeholder-slate-500 shadow-inner outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20"
            />

            {error && <p className="text-xs font-semibold text-rose-400">{error}</p>}

            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-400">Supervisor will auto-plan DAG dependencies</span>
              <button
                type="submit"
                disabled={submitting || !goal.trim()}
                className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 px-5 py-2.5 text-xs font-bold text-white shadow-lg shadow-indigo-500/30 transition hover:from-indigo-500 hover:to-purple-500 disabled:opacity-50 hover:scale-[1.02]"
              >
                <IconPlay className="w-3.5 h-3.5" />
                <span>{submitting ? "Analyzing & Planning..." : "Launch Execution"}</span>
              </button>
            </div>
          </form>

          {/* Quick Starter Templates */}
          <div className="pt-4 border-t border-border/60">
            <p className="text-xs font-semibold text-slate-400 mb-3">Or choose a pre-configured goal:</p>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
              {QUICK_GOALS.map((q, idx) => (
                <div
                  key={idx}
                  onClick={() => setGoal(q.prompt)}
                  className="cursor-pointer rounded-xl border border-border/60 bg-surface-muted/60 p-4 hover:border-indigo-500/40 hover:bg-surface-muted transition group"
                >
                  <span className="inline-block rounded-full bg-indigo-500/10 px-2 py-0.5 text-[10px] font-semibold text-indigo-400 border border-indigo-500/20 mb-2">
                    {q.badge}
                  </span>
                  <h4 className="text-xs font-bold text-slate-200 group-hover:text-indigo-300 transition">
                    {q.title}
                  </h4>
                  <p className="text-[11px] text-slate-400 mt-1 line-clamp-2">{q.prompt}</p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Saved Workflows Section */}
        <div className="space-y-4">
          <h2 className="text-base font-bold text-white">Predefined Workflow Catalog</h2>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {workflows.map((w) => (
              <Link
                key={w.id}
                href={`/workflows/${w.id}`}
                className="group rounded-2xl border border-border/80 bg-surface-card p-5 shadow-lg hover:border-indigo-500/40 hover:bg-surface-card/80 transition"
              >
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-bold text-white group-hover:text-indigo-300 transition">
                    {w.name}
                  </h3>
                  <span className="text-xs text-indigo-400 group-hover:translate-x-1 transition">
                    Run →
                  </span>
                </div>
                <p className="text-xs text-slate-400 mt-1">
                  {w.description || "Deterministic multi-step agent workflow pipeline."}
                </p>
                <div className="flex items-center gap-3 text-[11px] text-slate-500 mt-3 font-mono">
                  <span>{w.definition?.nodes?.length ?? 0} Nodes</span>
                  <span>•</span>
                  <span>{w.definition?.edges?.length ?? 0} Edges</span>
                </div>
              </Link>
            ))}
            {workflows.length === 0 && (
              <div className="col-span-2 rounded-2xl border border-dashed border-border p-8 text-center text-xs text-slate-500">
                No predefined workflows registered. You can run any goal dynamically above!
              </div>
            )}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
