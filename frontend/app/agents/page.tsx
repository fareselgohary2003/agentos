"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import AppShell from "@/components/AppShell";
import { api } from "@/lib/api";
import { IconAgents } from "@/components/Icons";

export default function AgentsPage() {
  const [agents, setAgents] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listAgents().then(setAgents).catch((e) => setError(e.message));
  }, []);

  return (
    <AppShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
            <IconAgents className="w-6 h-6 text-indigo-400" />
            AI Agent Workforce
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Specialized autonomous roles configured with domain tools, system policies, and LLM backends
          </p>
        </div>

        {error && <p className="text-xs text-rose-400">{error}</p>}

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {agents.map((a) => (
            <div
              key={a.id}
              className="rounded-2xl border border-border/80 bg-surface-card p-6 shadow-xl space-y-4 hover:border-indigo-500/40 transition group"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 group-hover:scale-105 transition">
                    <IconAgents className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-white group-hover:text-indigo-300 transition">
                      {a.name}
                    </h3>
                    <p className="text-[11px] font-mono text-indigo-400">{a.model}</p>
                  </div>
                </div>
                <span className="rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-semibold text-emerald-400 border border-emerald-500/20">
                  {a.status || "active"}
                </span>
              </div>

              <p className="text-xs text-slate-300 line-clamp-2">
                {a.description || "Autonomous agent specialized in execution tasks."}
              </p>

              <div className="pt-2 border-t border-border/60">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
                  Allowed Tools:
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {(a.allowed_tools || []).map((t: string) => (
                    <span
                      key={t}
                      className="rounded-md bg-surface-muted px-2 py-0.5 text-[10px] font-mono text-slate-300 border border-border/60"
                    >
                      {t}
                    </span>
                  ))}
                  {(!a.allowed_tools || a.allowed_tools.length === 0) && (
                    <span className="text-[10px] text-slate-500">None assigned</span>
                  )}
                </div>
              </div>
            </div>
          ))}

          {agents.length === 0 && (
            <div className="col-span-3 rounded-2xl border border-dashed border-border p-12 text-center text-xs text-slate-500">
              Loading agent catalog...
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
