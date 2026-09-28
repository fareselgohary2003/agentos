"use client";

import React, { ReactNode } from "react";
import Sidebar from "@/components/Sidebar";
import Link from "next/link";
import { IconPlay } from "./Icons";

export default function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen bg-surface text-slate-100 antialiased selection:bg-blue-600 selection:text-white">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        {/* Clean SaaS Header */}
        <header className="h-14 border-b border-border bg-surface-muted/60 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-10">
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <span className="font-medium text-slate-300">Brightleaf Home Goods</span>
            <span>/</span>
            <span className="text-slate-400">Analytics & Automation</span>
          </div>

          <div className="flex items-center gap-3">
            <Link
              href="/workflows"
              className="flex items-center gap-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 px-3 py-1.5 text-xs font-semibold text-white shadow-sm transition"
            >
              <IconPlay className="w-3 h-3" />
              <span>Run Analysis</span>
            </Link>
          </div>
        </header>

        {/* Main Content Area */}
        <main className="flex-1 p-6 md:p-8 overflow-y-auto max-w-7xl w-full mx-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
