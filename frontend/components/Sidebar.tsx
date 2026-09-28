"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { api } from "@/lib/api";
import {
  IconDashboard,
  IconAgents,
  IconWorkflows,
  IconExecutions,
  IconApprovals,
  IconTools,
  IconEvaluations,
  IconMonitoring,
  IconAuditLogs,
} from "./Icons";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Overview", icon: IconDashboard },
  { href: "/workflows", label: "Workflows & Goals", icon: IconWorkflows },
  { href: "/executions", label: "Executions", icon: IconExecutions },
  { href: "/agents", label: "Agents Fleet", icon: IconAgents },
  { href: "/tools", label: "Tool Catalog", icon: IconTools },
  { href: "/approvals", label: "Approvals", icon: IconApprovals },
  { href: "/evaluations", label: "Quality Evals", icon: IconEvaluations },
  { href: "/monitoring", label: "Usage & Cost", icon: IconMonitoring },
  { href: "/audit-logs", label: "Audit Logs", icon: IconAuditLogs },
];

export default function Sidebar() {
  const pathname = usePathname();
  const [userName, setUserName] = useState("Fares Elgohary");
  const [userEmail, setUserEmail] = useState("fares@brightleafhome.com");

  useEffect(() => {
    api.me().then((u: any) => {
      if (u?.full_name) setUserName(u.full_name);
      if (u?.email) setUserEmail(u.email);
    }).catch(() => {});
  }, []);

  return (
    <aside className="w-60 shrink-0 flex flex-col border-r border-border bg-surface-muted/95 min-h-screen">
      {/* Brand Header */}
      <div className="p-4 border-b border-border">
        <Link href="/dashboard" className="flex items-center gap-2.5 group">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-600 font-bold text-white shadow-sm group-hover:bg-blue-500 transition">
            AO
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold tracking-tight text-white">AgentOS</span>
              <span className="rounded bg-blue-500/10 px-1.5 py-0.2 text-[10px] font-semibold text-blue-400 border border-blue-500/20">
                PRO
              </span>
            </div>
            <p className="text-[11px] text-slate-400">Enterprise Workspace</p>
          </div>
        </Link>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 px-3 py-3 space-y-1">
        <div className="px-2.5 pb-2 text-[10px] font-bold uppercase tracking-wider text-slate-500">
          Navigation
        </div>
        {NAV_ITEMS.map((item) => {
          const active = pathname === item.href || (item.href !== "/dashboard" && pathname?.startsWith(item.href));
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-xs font-medium transition ${
                active
                  ? "bg-blue-600 text-white shadow-sm"
                  : "text-slate-400 hover:bg-surface-card hover:text-slate-200"
              }`}
            >
              <Icon
                className={`w-4 h-4 ${
                  active ? "text-white" : "text-slate-400"
                }`}
              />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* User Info Card: Fares Elgohary */}
      <div className="p-3 border-t border-border space-y-2">
        <div className="flex items-center justify-between rounded-lg bg-surface-card p-2.5 border border-border/80">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="h-8 w-8 rounded-full bg-blue-600 flex items-center justify-center text-xs font-bold text-white shrink-0">
              FG
            </div>
            <div className="min-w-0">
              <p className="text-xs font-semibold text-white truncate">{userName}</p>
              <p className="text-[10px] text-slate-400 truncate">{userEmail}</p>
            </div>
          </div>
          <Link
            href="/login"
            className="text-[11px] text-slate-400 hover:text-rose-400 ml-1"
            title="Sign out"
          >
            ↪
          </Link>
        </div>
      </div>
    </aside>
  );
}
