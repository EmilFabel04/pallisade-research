"use client";

import { REPORT_LANES } from "@/lib/debate";

/** Glyph per stage — mirrors the specialist glyphs on the Agents page, then
 *  the synthesis stages. Keyed by report key so it stays in step with
 *  REPORT_LANES. */
const GLYPH: Record<string, string> = {
  market_report: "◫",
  sentiment_report: "◑",
  news_report: "☰",
  fundamentals_report: "▦",
  investment_plan: "⇄",
  trader_investment_plan: "⚑",
  final_trade_decision: "◆",
};

/** A static preview of the seven-stage debate flow. Numbered because a debate
 *  IS a sequence — each stage reads the ones before it. */
export function DebatePipeline() {
  return (
    <section className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-2)] p-5 shadow-[var(--shadow-card)]">
      <h2 className="mb-4 font-mono text-[10px] uppercase tracking-widest text-[var(--color-fg-muted)]">
        How a debate unfolds
      </h2>
      <ol className="relative">
        {REPORT_LANES.map((lane, i) => {
          const last = i === REPORT_LANES.length - 1;
          return (
            <li key={lane.key} className="relative flex items-center gap-3 pb-4 last:pb-0">
              {/* connector line */}
              {!last && (
                <span
                  aria-hidden
                  className="absolute left-[13px] top-7 h-[calc(100%-1.75rem)] w-px bg-[var(--color-border)]"
                />
              )}
              <span
                aria-hidden
                className={`z-10 flex h-7 w-7 shrink-0 items-center justify-center rounded-md border font-mono text-sm ${
                  lane.verdict
                    ? "border-[var(--color-accent)] bg-[var(--color-accent-soft)] text-[var(--color-accent)]"
                    : "border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-fg-dim)]"
                }`}
              >
                {GLYPH[lane.key] ?? "•"}
              </span>
              <span className="flex flex-1 items-baseline justify-between gap-3">
                <span className="font-mono text-[13px] text-[var(--color-fg)]">
                  {lane.agent}
                </span>
                <span className="font-mono text-[10px] uppercase tracking-wider text-[var(--color-fg-muted)]">
                  {lane.role}
                </span>
              </span>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
