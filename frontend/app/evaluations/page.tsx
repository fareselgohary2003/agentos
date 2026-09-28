"use client";

import React, { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { api } from "@/lib/api";
import { IconEvaluations } from "@/components/Icons";

export default function EvaluationsPage() {
  const [evaluations, setEvaluations] = useState<any[]>([]);

  useEffect(() => {
    api.listEvaluations().then(setEvaluations).catch(() => {});
  }, []);

  return (
    <AppShell>
      <div className="space-y-6 max-w-4xl mx-auto">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
            <IconEvaluations className="w-6 h-6 text-indigo-400" />
            Evaluation Benchmark Runs
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Deterministic regression tests and automated quality scorecards across agent datasets
          </p>
        </div>

        <div className="space-y-3">
          {evaluations.map((e) => {
            const pass = (e.score ?? 0) >= 0.8;
            return (
              <div
                key={e.id}
                className="rounded-2xl border border-border/80 bg-surface-card p-5 shadow-xl flex items-center justify-between hover:border-indigo-500/40 transition"
              >
                <div>
                  <h3 className="text-sm font-bold text-white">{e.dataset_name || "Evaluation Run"}</h3>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Executed: {new Date(e.created_at).toLocaleString()}
                  </p>
                </div>

                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <span className="text-[10px] uppercase font-bold text-slate-400 block">
                      Quality Score
                    </span>
                    <span
                      className={`text-lg font-black ${
                        pass ? "text-emerald-400" : "text-amber-400"
                      }`}
                    >
                      {((e.score ?? 0) * 100).toFixed(0)}%
                    </span>
                  </div>
                  <span
                    className={`rounded-full border px-2.5 py-1 text-xs font-bold ${
                      pass
                        ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
                        : "border-amber-500/30 bg-amber-500/10 text-amber-400"
                    }`}
                  >
                    {pass ? "Passed" : "Needs Review"}
                  </span>
                </div>
              </div>
            );
          })}

          {evaluations.length === 0 && (
            <div className="rounded-2xl border border-dashed border-border p-12 text-center text-xs text-slate-500">
              No evaluation test suites recorded yet.
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
