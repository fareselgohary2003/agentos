"use client";

import React, { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { api } from "@/lib/api";
import { IconAuditLogs } from "@/components/Icons";

export default function AuditLogsPage() {
  const [logs, setLogs] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listAuditLogs().then(setLogs).catch((e) => setError(e.message));
  }, []);

  return (
    <AppShell>
      <div className="space-y-6 max-w-5xl mx-auto">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
            <IconAuditLogs className="w-6 h-6 text-indigo-400" />
            Immutable Audit Logs
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Cryptographic ledger of agent decisions, tool invocations, user approvals, and tenant security events
          </p>
        </div>

        {error && <p className="text-xs text-rose-400">{error}</p>}

        <div className="overflow-hidden rounded-2xl border border-border/80 bg-surface-card shadow-xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-surface-muted text-slate-400 font-semibold border-b border-border/60">
                <tr>
                  <th className="px-5 py-3.5 uppercase tracking-wider">Action Event</th>
                  <th className="px-5 py-3.5 uppercase tracking-wider">Target Resource</th>
                  <th className="px-5 py-3.5 uppercase tracking-wider">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/40">
                {logs.map((log) => (
                  <tr key={log.id} className="hover:bg-surface-muted/50 transition">
                    <td className="px-5 py-3.5 font-semibold text-white">
                      <span className="font-mono text-indigo-300 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20">
                        {log.action}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 text-slate-300 font-mono max-w-md truncate">
                      {log.resource}
                    </td>
                    <td className="px-5 py-3.5 text-slate-400">
                      {new Date(log.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
                {logs.length === 0 && (
                  <tr>
                    <td colSpan={3} className="px-5 py-12 text-center text-slate-500">
                      No security audit entries recorded yet.
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
