"use client";

import type { LucideIcon } from "lucide-react";
import { TrendingUp, TrendingDown, ShieldAlert, ArrowDown } from "lucide-react";
import { Badge } from "@/app/_ui";
import { extractTakeaway, parseFields, ratingTone } from "@/lib/debate";
import type { DebateRunState } from "./useDebateStream";

const LINE_ICON: Record<string, { icon: LucideIcon; tone: string }> = {
  Bull: { icon: TrendingUp, tone: "var(--color-positive)" },
  Bear: { icon: TrendingDown, tone: "var(--color-negative)" },
  Risk: { icon: ShieldAlert, tone: "var(--color-fg-muted)" },
};

export function DebateSummary({ state }: { state: DebateRunState }) {
  const pm = state.reports["final_trade_decision"];
  if (!pm) return null;

  const f = parseFields(pm);
  const rating = f["Rating"] ?? "—";
  const conviction = f["Conviction"];
  const fairValue = f["Fair Value"];
  const horizon = f["Time Horizon"];

  const lastBull = [...state.turns].reverse().find((t) => t.speaker === "bull");
  const lastBear = [...state.turns].reverse().find((t) => t.speaker === "bear");
  const bullT = lastBull ? extractTakeaway(lastBull.text) : null;
  const bearT = lastBear ? extractTakeaway(lastBear.text) : null;
  const riskT = extractTakeaway(state.reports["trader_investment_plan"] ?? "");

  const lines: Array<[string, string | null]> = [
    ["Bull", bullT],
    ["Bear", bearT],
    ["Risk", riskT],
  ];

  return (
    <section className="elevated mb-4 rounded-lg border border-[var(--color-border)] p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-lg font-semibold">{state.ticker ?? ""}</span>
          <span className="opacity-50">—</span>
          <Badge tone={ratingTone(rating)}>{rating}</Badge>
          {conviction && (
            <span className="text-sm text-[var(--color-fg-dim)]">
              conviction {conviction.toLowerCase()}
            </span>
          )}
        </div>
        <a
          href="#verdict"
          className="shrink-0 inline-flex items-center gap-1 font-mono text-[11px] uppercase tracking-wider text-[var(--color-accent)] hover:underline"
        >
          <ArrowDown size={13} strokeWidth={1.75} aria-hidden="true" /> jump to verdict
        </a>
      </div>

      {(fairValue || horizon) && (
        <p className="mt-1 text-sm text-[var(--color-fg-dim)]">
          {[fairValue && `Fair value ${fairValue}`, horizon && `horizon ${horizon}`]
            .filter(Boolean)
            .join(" · ")}
        </p>
      )}

      <dl className="mt-3 grid gap-1.5">
        {lines.map(([label, text]) => {
          const meta = LINE_ICON[label];
          const Icon = meta?.icon;
          return (
            <div key={label} className="flex items-center gap-3 text-sm">
              <dt className="flex w-14 shrink-0 items-center gap-1.5 font-mono text-[11px] uppercase tracking-wider text-[var(--color-fg-muted)]">
                {Icon && <Icon size={12} strokeWidth={2} style={{ color: meta.tone }} />}
                {label}
              </dt>
              <dd className="min-w-0 flex-1 truncate text-[var(--color-fg-dim)]">
                {text ?? "—"}
              </dd>
            </div>
          );
        })}
      </dl>
    </section>
  );
}
