"use client";

import { useEffect, useState } from "react";
import { PageHeader } from "@/app/_ui";
import { createDebateRun, listDebateRuns, REPORT_LANES, type DebateRunSummary } from "@/lib/debate";
import { LaneBoard } from "../debate/_ui/LaneBoard";
import { useDebateStream } from "../debate/_ui/useDebateStream";
import { AnalystLaunchpad } from "./_ui/AnalystLaunchpad";
import { RunHistoryList } from "../_ui-shared/RunHistoryList";

const ANALYST_TO_REPORT: Record<string, string> = {
  market: "market_report", social: "sentiment_report",
  news: "news_report", fundamentals: "fundamentals_report",
};

export default function AgentsPage() {
  const [runId, setRunId] = useState<string | null>(null);
  const [runAnalysts, setRunAnalysts] = useState<string[]>([]);
  const [initialTicker, setInitialTicker] = useState("");
  const [history, setHistory] = useState<DebateRunSummary[]>([]);
  const [launchError, setLaunchError] = useState<string | null>(null);

  const state = useDebateStream(runId);

  useEffect(() => {
    const s = new URLSearchParams(window.location.search).get("subject");
    if (s) setInitialTicker(s);
  }, []);

  function refreshHistory() {
    listDebateRuns("analysts").then((d) => setHistory(d.runs)).catch(() => setHistory([]));
  }
  useEffect(refreshHistory, [runId]);

  async function launch(input: { ticker: string; analysts: string[] }) {
    setLaunchError(null);
    setRunAnalysts(input.analysts);
    try {
      const { run_id } = await createDebateRun({
        ticker: input.ticker, rounds: 1, analysts: input.analysts, analystsOnly: true,
      });
      setRunId(run_id);
    } catch {
      setLaunchError(`Couldn't run the analysts for "${input.ticker}". Check the ticker and try again.`);
    }
  }

  // Lanes to show: the selected analysts (active run) or, when reopening from
  // history before analysts are known, every analyst lane that has a report.
  const shownKeys = runAnalysts.length
    ? runAnalysts.map((a) => ANALYST_TO_REPORT[a])
    : REPORT_LANES.filter((l) => state.reports[l.key] && !l.verdict).map((l) => l.key);
  const lanes = REPORT_LANES.filter((l) => shownKeys.includes(l.key));

  return (
    <div>
      <PageHeader eyebrow="Multi-agent" title="Agents" />
      <p
        className="mb-8 max-w-2xl text-sm leading-relaxed text-[var(--color-fg-dim)]"
        style={{ marginTop: "-1.25rem" }}
      >
        Pull any specialist&rsquo;s read on a ticker &mdash; market, sentiment, news, or
        fundamentals &mdash; without running a full debate.
      </p>
      {runId ? (
        <div className="space-y-6">
          <button
            onClick={() => { setRunId(null); setRunAnalysts([]); }}
            className="font-mono text-[10px] uppercase tracking-wider text-[var(--color-fg-muted)] transition-colors duration-150 hover:text-[var(--color-fg)]"
          >
            ← New analyst run
          </button>
          <LaneBoard state={state} lanes={lanes} showTranscript={false} showVerdict={false} />
        </div>
      ) : (
        <div className="grid grid-cols-12 gap-8">
          <div className="col-span-12 lg:col-span-8 space-y-6">
            <AnalystLaunchpad initialTicker={initialTicker} onRun={launch} />
            {launchError && (
              <div className="rounded-md border border-[var(--color-negative)]/40 bg-[var(--color-negative)]/5 px-4 py-3 font-mono text-xs text-[var(--color-negative)]">
                {launchError}
              </div>
            )}
          </div>
          <aside className="col-span-12 lg:col-span-4">
            <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)]">
              <div className="border-b border-[var(--color-border)] px-4 py-3 font-mono text-[10px] uppercase tracking-wider text-[var(--color-fg-muted)]">
                Past analyst runs
              </div>
              <RunHistoryList runs={history} emptyLabel="No analyst runs yet — run one above." showAnalysts onOpen={setRunId} />
            </div>
          </aside>
        </div>
      )}
    </div>
  );
}
