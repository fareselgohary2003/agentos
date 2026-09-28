"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { api } from "@/lib/api";

export default function AgentDetailPage({ params }: { params: { id: string } }) {
  const [agent, setAgent] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getAgent(params.id).then(setAgent).catch((e) => setError(e.message));
  }, [params.id]);

  if (error) return <AppShell><p className="p-8 text-sm text-red-500">{error}</p></AppShell>;
  if (!agent) return <AppShell><p className="p-8 text-sm text-slate-500">Loading…</p></AppShell>;

  const fields: [string, any][] = [
    ["Description", agent.description || "—"],
    ["Model", agent.model],
    ["Temperature", agent.temperature],
    ["Max Iterations", agent.max_iterations],
    ["Allowed Tools", agent.allowed_tools.join(", ") || "none"],
    ["Status", agent.status],
    ["Version", agent.version],
  ];

  return (
    <AppShell>
      <main className="mx-auto max-w-3xl p-8">
        <h1 className="mb-6 text-2xl font-semibold">{agent.name}</h1>
        <dl className="grid grid-cols-2 gap-4 rounded-xl border border-border bg-surface-muted p-6">
          {fields.map(([label, value]) => (
            <div key={label}>
              <dt className="text-xs uppercase tracking-wide text-slate-500">{label}</dt>
              <dd className="mt-1 text-sm">{String(value)}</dd>
            </div>
          ))}
        </dl>
      </main>
    </AppShell>
  );
}
