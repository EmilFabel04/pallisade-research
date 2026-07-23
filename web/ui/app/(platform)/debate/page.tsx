"use client";

import { useEffect, useState } from "react";
import { PageHeader, Button } from "@/app/_ui";
import { createDebateRun, listDebateRuns, type DebateRunSummary } from "@/lib/debate";
import { debatePdfUrl, openPdf } from "@/lib/export";
import { Launchpad } from "./_ui/Launchpad";
import { LaneBoard } from "./_ui/LaneBoard";
import { DebatePipeline } from "./_ui/DebatePipeline";
import { useDebateStream } from "./_ui/useDebateStream";
import { RunHistoryList } from "../_ui-shared/RunHistoryList";

export default function DebatePage() {
  const [runId, setRunId] = useState<string | null>(null);
  const [initialTicker, setInitialTicker] = useState("");
  const [history, setHistory] = useState<DebateRunSummary[]>([]);
  const [launchError, setLaunchError] = useState<string | null>(null);

  const state = useDebateStream(runId);

  useEffect(() => {
    const s = new URLSearchParams(window.location.search).get("subject");
    if (s) setInitialTicker(s);
  }, []);

  function refreshHistory() {
    listDebateRuns("debate")
      .then((d) => setHistory(d.runs))
      .catch(() => setHistory([]));
  }

  useEffect(refreshHistory, [runId]);

  async function launch(input: { ticker: string; rounds: number }) {
    setLaunchError(null);
    try {
      const { run_id } = await createDebateRun(input);
      setRunId(run_id);
    } catch {
      setLaunchError(`Couldn't start a debate for "${input.ticker}". Check the ticker and try again.`);
    }
  }

  return (
    <div>
      <PageHeader eyebrow="Multi-agent" title="Debate" />
      <p
        className="mb-8 max-w-2xl text-sm leading-relaxed text-[var(--color-fg-dim)]"
        style={{ marginTop: "-1.25rem" }}
      >
        Put a ticker through the full room &mdash; four analysts, a bull-vs-bear
        argument, a red-team pre-mortem, and a portfolio-manager verdict.
      </p>

      {runId ? (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <button
              onClick={() => setRunId(null)}
              className="font-mono text-[10px] uppercase tracking-wider text-[var(--color-fg-muted)] transition-colors duration-150 hover:text-[var(--color-fg)]"
            >
              ← New debate
            </button>
            {runId && state.phase === "done" && (
              <Button size="sm" variant="ghost" onClick={() => openPdf(debatePdfUrl(runId))}>
                ↓ PDF
              </Button>
            )}
          </div>
          <LaneBoard state={state} />
        </div>
      ) : (
        <div className="grid grid-cols-12 gap-8">
          <div className="col-span-12 lg:col-span-8 space-y-6">
            <Launchpad initialTicker={initialTicker} onRun={launch} />
            {launchError && (
              <div className="rounded-md border border-[var(--color-negative)]/40 bg-[var(--color-negative)]/5 px-4 py-3 font-mono text-xs text-[var(--color-negative)]">
                {launchError}
              </div>
            )}
            <DebatePipeline />
          </div>
          <aside className="col-span-12 lg:col-span-4">
            <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)]">
              <div className="border-b border-[var(--color-border)] px-4 py-3 font-mono text-[10px] uppercase tracking-wider text-[var(--color-fg-muted)]">
                Past debates
              </div>
              <RunHistoryList runs={history} emptyLabel="No debates yet." onOpen={setRunId} />
            </div>
          </aside>
        </div>
      )}
    </div>
  );
}
