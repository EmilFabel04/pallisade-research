"use client";

import { timeAgo, absoluteTime } from "@/lib/time";
import type { DebateRunSummary } from "@/lib/debate";

const ANALYST_LABEL: Record<string, string> = {
  market: "Market", social: "Sentiment", news: "News", fundamentals: "Fundamentals",
};

function dotClass(status: string): string {
  if (status === "done") return "bg-[var(--color-positive)]";
  if (status === "failed" || status === "error") return "bg-[var(--color-negative)]";
  return "bg-[var(--color-accent)] pulse-dot"; // queued / running
}

export function RunHistoryList({
  runs, emptyLabel, showAnalysts = false, onOpen,
}: {
  runs: DebateRunSummary[];
  emptyLabel: string;
  showAnalysts?: boolean;
  onOpen: (id: string) => void;
}) {
  if (runs.length === 0) {
    return (
      <div className="flex flex-col items-center gap-2 px-4 py-10 text-center">
        <span aria-hidden className="font-mono text-2xl leading-none text-[var(--color-fg-muted)] opacity-40">
          ◎
        </span>
        <p className="text-xs text-[var(--color-fg-dim)]">{emptyLabel}</p>
      </div>
    );
  }
  return (
    <ul className="divide-y divide-[var(--color-border)]">
      {runs.map((r) => (
        <li key={r.id}>
          <button
            onClick={() => onOpen(r.id)}
            className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left transition hover:bg-[var(--color-surface-2)]"
          >
            <span className="min-w-0">
              <span className="flex items-center gap-2">
                <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${dotClass(r.status)}`} />
                <span className="font-mono text-sm">{r.ticker}</span>
              </span>
              {showAnalysts && r.analysts && r.analysts.length > 0 && (
                <span className="mt-1 block pl-3.5 font-mono text-[10px] text-[var(--color-fg-muted)]">
                  {r.analysts.map((a) => ANALYST_LABEL[a] ?? a).join(" · ")}
                </span>
              )}
            </span>
            <span
              title={absoluteTime(r.created_at)}
              className="shrink-0 font-mono text-[10px] tabular-nums text-[var(--color-fg-muted)]"
            >
              {timeAgo(r.created_at)}
            </span>
          </button>
        </li>
      ))}
    </ul>
  );
}
