"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Badge, Button, EmptyState, Skeleton, type BadgeTone } from "../../_ui";

interface RunSummary {
  id: string;
  ticker: string;
  trade_date: string;
  status: "queued" | "running" | "done" | "error";
  created_at: string;
}

function statusTone(status: RunSummary["status"]): BadgeTone {
  switch (status) {
    case "done":    return "ok";
    case "running": return "warn";
    case "queued":  return "info";
    case "error":   return "err";
  }
}

export default function HistoryPage() {
  const [runs, setRuns] = useState<RunSummary[] | null>(null);

  useEffect(() => {
    api<{ runs: RunSummary[] }>("/api/runs")
      .then((d) => setRuns(d.runs))
      .catch(() => setRuns([]));
  }, []);

  return (
    <main>
      <header className="mb-8">
        <div className="font-mono text-xs uppercase tracking-widest text-[var(--color-fg-muted)]">
          History
        </div>
        <h1 className="mt-1 text-3xl font-medium tracking-tight">Past dossiers</h1>
      </header>

      <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[var(--color-border)] text-left font-mono text-[10px] uppercase tracking-wider text-[var(--color-fg-muted)]">
              <th className="px-4 py-3">Ticker</th>
              <th className="px-4 py-3">Trade date</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Created</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody>
            {runs === null && Array.from({ length: 5 }).map((_, i) => (
              <tr key={`skel-${i}`} className="border-b border-[var(--color-border)]">
                <td className="px-4 py-3"><Skeleton className="h-3 w-16" /></td>
                <td className="px-4 py-3"><Skeleton className="h-3 w-24" /></td>
                <td className="px-4 py-3"><Skeleton className="h-3 w-14" /></td>
                <td className="px-4 py-3"><Skeleton className="h-3 w-28" /></td>
                <td className="px-4 py-3"><Skeleton className="h-3 w-10" /></td>
              </tr>
            ))}
            {runs?.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-6">
                  <EmptyState
                    icon={
                      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M3 3v18h18" />
                        <path d="M7 14l4-5 3 3 5-7" />
                      </svg>
                    }
                    title="No dossiers yet"
                    hint="Start one to populate this view"
                    action={
                      <Button onClick={() => (window.location.href = "/public")}>
                        Start dossier
                      </Button>
                    }
                  />
                </td>
              </tr>
            )}
            {runs?.map((r) => (
              <tr
                key={r.id}
                className="border-b border-[var(--color-border)] hover:bg-[var(--color-surface-2)] transition"
              >
                <td className="px-4 py-3 font-mono">{r.ticker}</td>
                <td className="px-4 py-3 font-mono text-[var(--color-fg-dim)]">{r.trade_date}</td>
                <td className="px-4 py-3">
                  <Badge tone={statusTone(r.status)}>{r.status}</Badge>
                </td>
                <td className="px-4 py-3 font-mono text-xs text-[var(--color-fg-muted)]">
                  {new Date(r.created_at).toLocaleString()}
                </td>
                <td className="px-4 py-3 text-right">
                  <Link
                    href={`/public/runs/${r.id}`}
                    className="font-mono text-xs text-[var(--color-accent)] hover:underline"
                  >
                    open →
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  );
}
