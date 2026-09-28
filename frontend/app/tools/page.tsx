"use client";

import React, { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { api } from "@/lib/api";
import { IconTools } from "@/components/Icons";

const RISK_BADGES: Record<string, { badge: string; text: string }> = {
  low: { badge: "bg-emerald-500/10 border-emerald-500/30 text-emerald-400", text: "Low Risk" },
  medium: { badge: "bg-amber-500/10 border-amber-500/30 text-amber-400", text: "Medium Risk" },
  high: { badge: "bg-rose-500/10 border-rose-500/30 text-rose-400", text: "High Risk" },
  critical: { badge: "bg-red-500/20 border-red-500/40 text-red-400", text: "Critical Risk" },
};

export default function ToolsPage() {
  const [data, setData] = useState<{ catalog: any[]; runtime_registered: string[] } | null>(null);

  useEffect(() => {
    api.listTools().then(setData).catch(() => {});
  }, []);

  return (
    <AppShell>
      <div className="space-y-6 max-w-5xl mx-auto">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
            <IconTools className="w-6 h-6 text-indigo-400" />
            Tool Registry & Capabilities
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Deterministic sandboxed execution tools, SQL query engines, web retrieval, and action dispatchers
          </p>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {(data?.catalog ?? []).map((t) => {
            const risk = RISK_BADGES[t.risk_level] ?? RISK_BADGES.low;
            return (
              <div
                key={t.id}
                className="rounded-2xl border border-border/80 bg-surface-card p-6 shadow-xl space-y-3 hover:border-indigo-500/40 transition"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-mono text-xs font-bold">
                      {"{ }"}
                    </div>
                    <h3 className="text-sm font-bold text-white font-mono">{t.name}</h3>
                  </div>
                  <span className={`rounded-full border px-2.5 py-0.5 text-[10px] font-semibold ${risk.badge}`}>
                    {risk.text}
                  </span>
                </div>

                <p className="text-xs text-slate-300 leading-relaxed">{t.description}</p>

                <div className="flex items-center justify-between pt-2 border-t border-border/60 text-xs">
                  <span className="text-slate-500 font-mono">ID: {t.id}</span>
                  <span className="flex items-center gap-1.5 text-emerald-400 font-semibold text-[11px]">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                    {t.is_enabled ? "Active in Sandbox" : "Disabled"}
                  </span>
                </div>
              </div>
            );
          })}

          {(!data?.catalog || data.catalog.length === 0) && (
            <div className="col-span-2 rounded-2xl border border-dashed border-border p-12 text-center text-xs text-slate-500">
              Loading runtime registered tools...
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
