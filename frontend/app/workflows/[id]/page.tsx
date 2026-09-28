"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import AppShell from "@/components/AppShell";
import { api } from "@/lib/api";

export default function WorkflowDetailPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const [workflow, setWorkflow] = useState<any>(null);
  const [goal, setGoal] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getWorkflow(params.id).then(setWorkflow).catch((e) => setError(e.message));
  }, [params.id]);

  async function run(e: React.FormEvent) {
    e.preventDefault();
    try {
      const { execution_id } = await api.executeWorkflow(params.id, goal);
      router.push(`/executions/${execution_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to execute");
    }
  }

  if (!workflow) return <AppShell><p className="p-8 text-sm text-slate-500">Loading…</p></AppShell>;

  return (
    <AppShell>
      <main className="mx-auto max-w-3xl p-8">
        <h1 className="mb-2 text-2xl font-semibold">{workflow.name}</h1>
        <p className="mb-6 text-xs text-slate-500">
          {workflow.definition?.nodes?.length ?? 0} nodes ·{" "}
          {workflow.definition?.edges?.length ?? 0} edges
        </p>

        <form onSubmit={run} className="rounded-xl border border-border bg-surface-muted p-5">
          <label className="mb-2 block text-sm font-medium">Goal for this run</label>
          <textarea
            required
            rows={2}
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            className="mb-3 w-full rounded-md border border-border bg-transparent px-3 py-2 text-sm outline-none focus:border-accent"
          />
          {error && <p className="mb-3 text-sm text-red-500">{error}</p>}
          <button type="submit" className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white">
            Execute
          </button>
        </form>
      </main>
    </AppShell>
  );
}
