"use client";

import { TrendingUp, TrendingDown } from "lucide-react";
import { Badge } from "@/app/_ui";
import { SPEAKER_META, type DebateTurn } from "@/lib/debate";
import type { DebateRunState } from "./useDebateStream";
import { CollapsibleMarkdown } from "./CollapsibleMarkdown";

function Bubble({
  turn,
  openMap,
  onOpen,
}: {
  turn: DebateTurn;
  openMap?: Record<string, boolean>;
  onOpen?: (key: string, open: boolean) => void;
}) {
  const meta = SPEAKER_META[turn.speaker] ?? { label: turn.speaker, side: "left" as const };
  const isBull = meta.side === "left";
  const tone = isBull ? "var(--color-positive)" : "var(--color-negative)";
  const key = `turn-${turn.seq}`;
  const badgeTone = turn.speaker === "bull" ? "bull" : turn.speaker === "bear" ? "bear" : "neutral";
  const SideIcon = turn.speaker === "bear" ? TrendingDown : TrendingUp;
  return (
    <div className={`flex gap-2.5 ${isBull ? "flex-row" : "flex-row-reverse"} items-end`}>
      <div
        className="flex h-7 w-7 flex-none items-center justify-center rounded-full border"
        style={{ borderColor: `color-mix(in srgb, ${tone} 40%, transparent)`,
                 background: `color-mix(in srgb, ${tone} 15%, transparent)`, color: tone }}
      >
        <SideIcon size={14} strokeWidth={2} aria-hidden="true" />
      </div>
      <div
        className={`max-w-[76%] rounded-xl border px-3.5 py-2.5 ${isBull ? "rounded-bl-sm" : "rounded-br-sm"}`}
        style={{ borderColor: `color-mix(in srgb, ${tone} 28%, transparent)`,
                 background: `color-mix(in srgb, ${tone} 8%, transparent)` }}
      >
        <CollapsibleMarkdown
          body={turn.text}
          chip={
            <Badge tone={badgeTone}>
              <SideIcon size={11} strokeWidth={2} aria-hidden="true" />
              {meta.label}
            </Badge>
          }
          timestamp={turn.ts}
          open={openMap?.[key]}
          onOpenChange={onOpen ? (o) => onOpen(key, o) : undefined}
        />
      </div>
    </div>
  );
}

function RoundDivider({ round }: { round: number }) {
  return (
    <div className="my-2 flex items-center gap-2 opacity-50">
      <span className="h-px flex-1 bg-[var(--color-border)]" />
      <span className="font-mono text-[9px] uppercase tracking-widest">Round {round}</span>
      <span className="h-px flex-1 bg-[var(--color-border)]" />
    </div>
  );
}

/** A turn is a 10-30s LLM call, so the wait needs filling. */
function Typing() {
  return (
    <div className="flex items-center gap-1 px-3 py-2">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="h-1 w-1 rounded-full bg-[var(--color-fg-muted)] pulse-dot"
          style={{ animationDelay: `${i * 0.18}s` }}
        />
      ))}
    </div>
  );
}

export function DebateTranscript({
  state,
  openMap,
  onOpen,
}: {
  state: DebateRunState;
  openMap?: Record<string, boolean>;
  onOpen?: (key: string, open: boolean) => void;
}) {
  const turns = state.turns;
  if (turns.length === 0 && state.phase !== "running") return null;

  // The bull/bear argument wraps up long before the run does — risk debate,
  // trader, and PM all still have to run after it. The Research Manager's
  // investment_plan report only appears once that argument has concluded, so
  // its presence is the signal that there are no more turns coming here.
  const debateOver = Boolean(state.reports["investment_plan"]);
  const isLive = state.phase === "running" && !debateOver;

  const rows: React.ReactNode[] = [];
  let lastRound = 0;
  for (const turn of turns) {
    if (turn.round !== lastRound) {
      rows.push(<RoundDivider key={`r${turn.round}`} round={turn.round} />);
      lastRound = turn.round;
    }
    rows.push(<Bubble key={turn.seq} turn={turn} openMap={openMap} onOpen={onOpen} />);
  }

  return (
    <section
      className="rounded-lg border p-5"
      style={{ borderColor: "color-mix(in srgb, var(--color-accent) 40%, transparent)",
               background: "var(--color-accent-soft)" }}
    >
      <div className="mb-4 font-mono text-[10px] uppercase tracking-widest text-[var(--color-accent)]">
        The Debate {isLive ? "· live" : ""}
      </div>
      <div className="space-y-3">
        {rows}
        {isLive && <Typing />}
        {rows.length === 0 && isLive && (
          <div className="font-mono text-[11px] text-[var(--color-fg-muted)]">
            Waiting for the researchers to open…
          </div>
        )}
      </div>
    </section>
  );
}
