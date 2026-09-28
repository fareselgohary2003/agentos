"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("fares@brightleafhome.com");
  const [password, setPassword] = useState("BrightleafDemo123");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function performLogin(loginEmail: string, loginPass: string) {
    setError(null);
    setLoading(true);
    try {
      const tokens = await api.login(loginEmail, loginPass);
      localStorage.setItem("access_token", tokens.access_token);
      localStorage.setItem("refresh_token", tokens.refresh_token);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed. Check credentials.");
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    performLogin(email, password);
  }

  return (
    <main className="flex min-h-screen items-center justify-center p-6 bg-surface">
      <div className="w-full max-w-sm rounded-2xl border border-border bg-surface-card p-8 shadow-md space-y-6">
        {/* Brand Header */}
        <div className="space-y-1">
          <div className="flex items-center gap-2.5 mb-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-600 font-bold text-white shadow-sm">
              AO
            </div>
            <div>
              <span className="text-base font-bold text-white">AgentOS</span>
              <p className="text-[11px] text-slate-400">Enterprise Data Workspace</p>
            </div>
          </div>
          <h1 className="text-lg font-semibold text-white">Sign in to your account</h1>
          <p className="text-xs text-slate-400">
            Welcome back, <span className="font-semibold text-slate-200">Fares Elgohary</span>
          </p>
        </div>

        {error && (
          <div className="rounded-lg border border-rose-500/30 bg-rose-950/20 p-2.5 text-xs text-rose-300">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-300">
              Work Email
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-xs text-white placeholder-slate-500 outline-none transition focus:border-blue-500"
            />
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-slate-300">
              Password
            </label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-xs text-white placeholder-slate-500 outline-none transition focus:border-blue-500"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-blue-600 py-2.5 text-xs font-semibold text-white shadow-sm hover:bg-blue-500 transition disabled:opacity-60"
          >
            {loading ? "Signing in..." : "Sign In"}
          </button>
        </form>

        <div className="pt-2 border-t border-border">
          <button
            type="button"
            onClick={() => performLogin("fares@brightleafhome.com", "BrightleafDemo123")}
            disabled={loading}
            className="w-full rounded-lg border border-border bg-surface-muted py-2 text-xs font-medium text-slate-300 hover:bg-surface hover:text-white transition"
          >
            Quick Sign In (Fares Elgohary)
          </button>
        </div>
      </div>
    </main>
  );
}
