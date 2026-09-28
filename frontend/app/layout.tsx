import "./globals.css";
import type { ReactNode } from "react";

export const metadata = {
  title: "AgentOS — Enterprise Autonomous AI Workforce Platform",
  description: "Create, orchestrate, and monitor AI agent workflows.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-surface text-slate-900 dark:text-slate-100 min-h-screen antialiased">
        {children}
      </body>
    </html>
  );
}
