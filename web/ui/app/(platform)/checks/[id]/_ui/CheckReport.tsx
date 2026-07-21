"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import {
  Badge,
  type BadgeTone,
  Card,
  Collapsible,
  EmptyState,
  KPI,
  Skeleton,
} from "@/app/_ui";
import { ApiError } from "@/lib/api";
import {
  getMemoCheck,
  type MemoCheckDetail,
  type MemoClaimResult,
  type Verdict,
} from "@/lib/memoChecks";
import { absoluteTime, timeAgo } from "@/lib/time";

const verdictTone: Record<Verdict, BadgeTone> = {
  match: "ok",
  mismatch: "err",
  stale: "warn",
  unsupported: "neutral",
};

const verdictLabel: Record<Verdict, string> = {
  match: "Matched",
  mismatch: "Mismatched",
  stale: "Stale",
  unsupported: "Unsupported",
};

function ReportSkeleton() {
  return (
    <div className="max-w-4xl space-y-6">
      <Skeleton className="h-4 w-32" />
      <Skeleton className="h-7 w-72" />
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-20 w-full" />
        ))}
      </div>
      <Skeleton className="h-40 w-full" />
      <Skeleton className="h-40 w-full" />
    </div>
  );
}

function ResultCard({ result }: { result: MemoClaimResult }) {
  const citation = result.locator
    ? `per ${result.locator}${result.source_as_of ? ` · ${result.source_as_of}` : ""}`
    : null;

  return (
    <div className="rounded-[12px] border border-[var(--color-border)] bg-[var(--color-surface)] p-4 transition-colors hover:border-[var(--color-fg-muted)]">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <p className="max-w-2xl text-sm text-[var(--color-fg-dim)]">
          {result.claim_text}
        </p>
        <Badge tone={verdictTone[result.verdict]}>
          {verdictLabel[result.verdict]}
        </Badge>
      </div>

      <p className="mt-2 text-lg text-[var(--color-fg)]">{result.claim_value}</p>

      {result.source_value && (
        <p className="mt-1 text-sm text-[var(--color-fg-dim)]">
          Source:{" "}
          <span className="text-[var(--color-fg)]">{result.source_value}</span>
        </p>
      )}

      {citation && (
        <p className="mt-1 font-mono text-[10px] uppercase tracking-wider text-[var(--color-fg-muted)]">
          {citation}
        </p>
      )}

      {result.rationale && (
        <p className="mt-3 border-t border-[var(--color-border)] pt-2 text-sm text-[var(--color-fg-dim)]">
          {result.rationale}
        </p>
      )}
    </div>
  );
}

export function CheckReport({ id }: { id: string }) {
  const [data, setData] = useState<MemoCheckDetail | null>(null);
  // Hard error: the check genuinely doesn't exist (404) — stop polling, no
  // amount of retrying will fix it.
  const [hardError, setHardError] = useState<string | null>(null);
  // Transient error: a network/5xx blip while polling. Non-blocking — the
  // poll keeps retrying and, if we already have data, we keep showing it.
  const [transientError, setTransientError] = useState<string | null>(null);

  useEffect(() => {
    let stop = false;
    async function tick() {
      try {
        const d = await getMemoCheck(id);
        if (stop) return;
        setData(d);
        setTransientError(null);
        if (d.check.status === "queued" || d.check.status === "running") {
          setTimeout(tick, 3000);
        }
      } catch (e) {
        if (stop) return;
        if (e instanceof ApiError && e.status === 404) {
          setHardError("This check couldn't be found.");
          return;
        }
        setTransientError((e as Error).message);
        // Keep polling — the check may still be running server-side and
        // this may just be a transient network/server blip.
        setTimeout(tick, 3000);
      }
    }
    tick();
    return () => {
      stop = true;
    };
  }, [id]);

  if (!data && hardError) {
    return (
      <EmptyState
        title="Couldn't load this check"
        hint={hardError}
        action={
          <Link
            className="font-mono text-[11px] uppercase tracking-wider text-[var(--color-accent)] hover:underline"
            href="/checks"
          >
            ← Back to checks
          </Link>
        }
      />
    );
  }

  if (!data) return <ReportSkeleton />;

  const { check, results } = data;
  const isRunning = check.status === "queued" || check.status === "running";

  const counts = results.reduce<Record<Verdict, number>>(
    (acc, r) => {
      acc[r.verdict] += 1;
      return acc;
    },
    { match: 0, mismatch: 0, stale: 0, unsupported: 0 }
  );

  return (
    <section className="max-w-4xl">
      <Link
        className="font-mono text-[11px] uppercase tracking-wider text-[var(--color-fg-muted)] underline-offset-4 hover:text-[var(--color-accent)] hover:underline"
        href="/checks"
      >
        ← All checks
      </Link>

      <div className="mt-4 flex flex-wrap items-baseline gap-3">
        <h2 className="text-xl">Check Report</h2>
        <span className="font-mono text-[11px] uppercase tracking-wider text-[var(--color-fg-muted)]">
          {check.id.slice(0, 8)}
        </span>
      </div>
      <p
        className="mt-1 text-xs text-[var(--color-fg-muted)]"
        title={absoluteTime(check.created_at)}
      >
        Started {timeAgo(check.created_at)}
      </p>

      {transientError && (
        <div
          role="alert"
          className="mt-4 flex items-center gap-3 rounded-md border border-[var(--color-negative)] px-3 py-2 font-mono text-xs text-[var(--color-negative)]"
        >
          <span>Couldn&apos;t reach the server. Showing the last loaded report.</span>
        </div>
      )}

      {check.status === "failed" && (
        <Card className="mt-6 border-[var(--color-accent)]">
          <div className="flex items-center gap-3">
            <Badge tone="err">Failed</Badge>
            <p className="text-sm text-[var(--color-fg)]">
              This check failed to complete.
            </p>
          </div>
        </Card>
      )}

      {isRunning && (
        <>
          <Card className="mt-6">
            <div className="flex items-center gap-3">
              <Badge tone="info">
                <span
                  className="h-1.5 w-1.5 rounded-full bg-current pulse-dot"
                  aria-hidden
                />
                {check.status === "queued" ? "Queued" : "Running"}
              </Badge>
              <p className="text-sm text-[var(--color-fg-dim)]">
                Checking figures…
              </p>
            </div>
          </Card>
          <div className="mt-6 space-y-3">
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-24 w-full" />
          </div>
        </>
      )}

      {check.status === "done" && (
        <>
          <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <KPI label="Matched" value={counts.match} />
            <KPI label="Mismatched" value={counts.mismatch} />
            <KPI label="Stale" value={counts.stale} />
            <KPI label="Unsupported" value={counts.unsupported} />
          </div>

          <div className="mt-6">
            <Collapsible
              label="Memo text"
              summary={check.memo_text.trim().replace(/\s+/g, " ").slice(0, 100)}
            >
              <Card className="whitespace-pre-wrap text-sm text-[var(--color-fg-dim)]">
                {check.memo_text}
              </Card>
            </Collapsible>
          </div>

          <div className="mt-8">
            <header className="mb-3 flex items-baseline justify-between">
              <h3 className="font-mono text-[10px] uppercase tracking-widest text-[var(--color-fg-muted)]">
                Results
              </h3>
              <span className="font-mono text-[10px] uppercase tracking-widest text-[var(--color-fg-muted)]">
                {results.length} figures
              </span>
            </header>
            {results.length === 0 ? (
              <EmptyState title="No cited figures found in this memo." />
            ) : (
              <div className="space-y-3">
                {results.map((r, i) => (
                  <ResultCard key={i} result={r} />
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </section>
  );
}
