"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";

import { Badge, type BadgeTone, Card, EmptyState, Skeleton } from "@/app/_ui";
import { listMemoChecks, type MemoCheck } from "@/lib/memoChecks";
import { absoluteTime, timeAgo } from "@/lib/time";

const statusTone: Record<MemoCheck["status"], BadgeTone> = {
  queued: "info",
  running: "info",
  done: "ok",
  failed: "err",
};

// Capitalized to match how CheckReport.tsx labels the same statuses.
const statusLabel: Record<MemoCheck["status"], string> = {
  queued: "Queued",
  running: "Running",
  done: "Done",
  failed: "Failed",
};

const PREVIEW_LEN = 80;

function truncate(text: string, max: number): string {
  const trimmed = text.trim().replace(/\s+/g, " ");
  return trimmed.length <= max ? trimmed : `${trimmed.slice(0, max)}…`;
}

export function ChecksList() {
  const [checks, setChecks] = useState<MemoCheck[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const { checks } = await listMemoChecks();
      setChecks(checks);
      setError(null);
    } catch (err) {
      setError((err as Error).message);
    }
  }, []);

  // Initial load.
  useEffect(() => {
    void load();
  }, [load]);

  // Poll every 3s while any check is non-terminal; stop once all are
  // terminal (or on unmount) by not scheduling a new interval.
  const inFlight = checks?.some(
    (c) => c.status === "queued" || c.status === "running"
  );
  useEffect(() => {
    if (!inFlight) return;
    const t = setInterval(() => void load(), 3000);
    return () => clearInterval(t);
  }, [inFlight, load]);

  if (checks === null && !error) {
    return (
      <div className="space-y-2">
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </div>
    );
  }

  // Only show the full error state when we have nothing else to show — a
  // failed load/poll shouldn't blank a list we already loaded successfully.
  if (error && (!checks || checks.length === 0)) {
    return (
      <div
        role="alert"
        className="flex items-center gap-3 rounded-md border border-[var(--color-negative)] px-3 py-2 font-mono text-xs text-[var(--color-negative)]"
      >
        <span>{error}</span>
        <button
          type="button"
          onClick={() => void load()}
          className="underline transition-colors hover:text-[var(--color-fg)]"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!checks || checks.length === 0) {
    return <EmptyState title="No checks yet — paste a memo above to run one" />;
  }

  return (
    <div>
      {error && (
        <div
          role="alert"
          className="mb-4 flex items-center gap-3 rounded-md border border-[var(--color-negative)] px-3 py-2 font-mono text-xs text-[var(--color-negative)]"
        >
          <span>Couldn&apos;t reach the server. Showing the last loaded list.</span>
          <button
            type="button"
            onClick={() => void load()}
            className="underline transition-colors hover:text-[var(--color-fg)]"
          >
            Retry
          </button>
        </div>
      )}
      <Card className="!p-0 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="border-b border-[var(--color-border)] text-left font-mono text-[10px] uppercase tracking-widest text-[var(--color-fg-muted)]">
            <tr>
              <th className="px-4 py-3">Memo</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3 text-right">Created</th>
            </tr>
          </thead>
          <tbody>
            {checks.map((c) => (
              <tr
                key={c.id}
                className="border-b border-[var(--color-border)] last:border-0 hover:bg-white/[0.015]"
              >
                <td className="px-4 py-3">
                  <Link
                    href={`/checks/${c.id}`}
                    className="text-[var(--color-fg)] hover:text-[var(--color-accent)] hover:underline"
                  >
                    {truncate(c.memo_text, PREVIEW_LEN) || "(empty memo)"}
                  </Link>
                </td>
                <td className="px-4 py-3">
                  <Badge tone={statusTone[c.status]}>{statusLabel[c.status]}</Badge>
                </td>
                <td
                  className="px-4 py-3 text-right font-mono text-[12px] text-[var(--color-fg-dim)]"
                  title={absoluteTime(c.created_at)}
                >
                  {timeAgo(c.created_at)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
