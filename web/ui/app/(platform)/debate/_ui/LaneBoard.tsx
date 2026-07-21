"use client";

import { useState } from "react";
import { Badge } from "@/app/_ui";
import { REPORT_LANES, parseFields, ratingTone, type LaneMeta } from "@/lib/debate";
import type { DebateRunState } from "./useDebateStream";
import { DebateTranscript } from "./DebateTranscript";
import { CollapsibleMarkdown } from "./CollapsibleMarkdown";
import { DebateSummary } from "./DebateSummary";

function laneStatus(
  state: DebateRunState,
  lanes: LaneMeta[],
  key: string,
  idx: number
): "pending" | "running" | "done" {
  if (state.reports[key]) return "done";
  // First not-yet-produced lane while running is the "running" one.
  if (state.phase === "running") {
    const firstMissing = lanes.findIndex((l) => !state.reports[l.key]);
    if (firstMissing === idx) return "running";
  }
  return "pending";
}

/** Rating/pre-mortem chip for a non-verdict lane row. */
function laneChip(key: string, body: string | undefined) {
  if (!body) return undefined;
  const f = parseFields(body);
  const rec = f["Recommendation"]; // Research Manager lane
  if (rec) {
    const conv = f["Conviction"];
    return (
      <Badge tone={ratingTone(rec)}>
        {conv ? `${rec} · ${conv.toLowerCase()}` : rec}
      </Badge>
    );
  }
  if (key === "trader_investment_plan") {
    return <Badge tone="neutral">pre-mortem</Badge>;
  }
  return undefined;
}

/** Rating chip for the verdict lane (reads **Rating**, not **Recommendation**). */
function verdictRatingChip(body: string) {
  const f = parseFields(body);
  const r = f["Rating"];
  if (!r) return undefined;
  const conv = f["Conviction"];
  return (
    <Badge tone={ratingTone(r)}>
      {conv ? `${r} · ${conv.toLowerCase()}` : r}
    </Badge>
  );
}

export function LaneBoard({
  state,
  lanes = REPORT_LANES,
  showTranscript = true,
  showVerdict = true,
}: {
  state: DebateRunState;
  lanes?: LaneMeta[];
  showTranscript?: boolean;
  showVerdict?: boolean;
}) {
  const verdictKey = "final_trade_decision";
  const verdict = state.reports[verdictKey];

  const [openMap, setOpenMap] = useState<Record<string, boolean>>({});

  function setOpen(key: string, open: boolean) {
    setOpenMap((m) => ({ ...m, [key]: open }));
  }
  function setAll(open: boolean) {
    const next: Record<string, boolean> = {};
    for (const l of lanes) next[l.key] = open;
    for (const t of state.turns) next[`turn-${t.seq}`] = open;
    setOpenMap(next);
  }

  return (
    <div className="space-y-4">
      {state.phase === "error" && state.error && (
        <div className="rounded-md border border-[var(--color-negative)]/40 bg-[var(--color-negative)]/5 p-4 font-mono text-sm text-[var(--color-negative)]">
          <div className="mb-1 text-xs uppercase tracking-wider opacity-80">Run failed</div>
          {state.error}
        </div>
      )}

      {showVerdict && state.phase === "done" && <DebateSummary state={state} />}

      <div className="mb-3 flex items-center gap-2">
        <button
          type="button"
          onClick={() => setAll(true)}
          className="font-mono text-[11px] uppercase tracking-wider text-[var(--color-fg-muted)] hover:text-[var(--color-fg)]"
        >
          ▾ Expand all
        </button>
        <button
          type="button"
          onClick={() => setAll(false)}
          className="font-mono text-[11px] uppercase tracking-wider text-[var(--color-fg-muted)] hover:text-[var(--color-fg)]"
        >
          ▸ Collapse all
        </button>
      </div>

      <ol className="space-y-3">
        {lanes.filter((l) => !l.verdict).map((lane, idx) => {
          const status = laneStatus(state, lanes.filter((l) => !l.verdict), lane.key, idx);
          const body = state.reports[lane.key];
          const dotClass = `h-1.5 w-1.5 rounded-full ${
            status === "done"
              ? "bg-[var(--color-positive)]"
              : status === "running"
              ? "bg-[var(--color-accent)] pulse-dot"
              : "bg-[var(--color-fg-muted)]"
          }`;
          return (
            <li
              key={lane.key}
              className={`rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-4 transition ${
                status === "pending" ? "opacity-50" : "opacity-100"
              }`}
            >
              {body ? (
                <CollapsibleMarkdown
                  body={body}
                  label={
                    <span className="flex items-center gap-2">
                      <span className={dotClass} />
                      {lane.agent}
                    </span>
                  }
                  chip={laneChip(lane.key, body)}
                  timestamp={state.reportTs[lane.key]}
                  open={openMap[lane.key] ?? false}
                  onOpenChange={(o) => setOpen(lane.key, o)}
                />
              ) : (
                <>
                  <div className="mb-2 flex items-center gap-2">
                    <span className={dotClass} />
                    <span className="font-mono text-sm">{lane.agent}</span>
                    <span className="font-mono text-[10px] uppercase tracking-wider text-[var(--color-fg-muted)]">
                      {lane.role}
                    </span>
                  </div>
                  <div className="space-y-2">
                    <div className="h-2 w-11/12 animate-pulse rounded bg-[var(--color-surface-2)]" />
                    <div className="h-2 w-3/4 animate-pulse rounded bg-[var(--color-surface-2)]" />
                  </div>
                </>
              )}
            </li>
          );
        })}
      </ol>

      {showTranscript && <DebateTranscript state={state} openMap={openMap} onOpen={setOpen} />}

      {showVerdict && (
        <div id="verdict">
          {verdict && (
            <div className="rounded-lg border border-[var(--color-accent)]/40 bg-[var(--color-accent-soft)] p-5">
              <CollapsibleMarkdown
                body={verdict}
                label={<span className="font-medium">Portfolio Manager · verdict</span>}
                chip={laneChip(verdictKey, verdict) ?? verdictRatingChip(verdict)}
                timestamp={state.reportTs[verdictKey]}
                open={openMap[verdictKey] ?? true}
                onOpenChange={(o) => setOpen(verdictKey, o)}
              />
            </div>
          )}
        </div>
      )}

      {state.statusLine && state.phase === "running" && (
        <div className="flex items-center gap-2 font-mono text-[11px] text-[var(--color-fg-muted)]">
          <span className="h-1.5 w-1.5 rounded-full bg-[var(--color-accent)] pulse-dot" />
          {state.statusLine}
        </div>
      )}
    </div>
  );
}
