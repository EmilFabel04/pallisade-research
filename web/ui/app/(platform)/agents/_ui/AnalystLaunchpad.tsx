"use client";

import { useState } from "react";

/** The four specialists. Wire keys stay `social` for the sentiment analyst. */
const ANALYSTS = [
  { key: "market", label: "Market", glyph: "◫", blurb: "Price action, momentum & technical levels" },
  { key: "social", label: "Sentiment", glyph: "◑", blurb: "Social chatter & retail positioning" },
  { key: "news", label: "News", glyph: "☰", blurb: "Catalysts, headlines & filings" },
  { key: "fundamentals", label: "Fundamentals", glyph: "▦", blurb: "Valuation & financial health" },
];

export function AnalystLaunchpad({
  initialTicker = "",
  onRun,
}: {
  initialTicker?: string;
  onRun: (input: { ticker: string; analysts: string[] }) => void;
}) {
  const [ticker, setTicker] = useState(initialTicker);
  const [selected, setSelected] = useState<Set<string>>(
    new Set(ANALYSTS.map((a) => a.key)),
  );

  function toggle(key: string) {
    setSelected((s) => {
      const next = new Set(s);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const t = ticker.trim();
    if (!t || selected.size === 0) return;
    onRun({ ticker: t, analysts: ANALYSTS.map((a) => a.key).filter((k) => selected.has(k)) });
  }

  const canRun = ticker.trim().length > 0 && selected.size > 0;

  return (
    <form onSubmit={submit} className="space-y-5">
      {/* ── specialist cards (the selector + the signature) ── */}
      <div>
        <div className="mb-3 flex items-center justify-between">
          <span className="font-mono text-[10px] uppercase tracking-widest text-[var(--color-fg-muted)]">
            Specialists
          </span>
          <span className="font-mono text-[10px] tabular-nums text-[var(--color-fg-muted)]">
            {selected.size} of {ANALYSTS.length} selected
          </span>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          {ANALYSTS.map((a) => {
            const on = selected.has(a.key);
            return (
              <button
                type="button"
                key={a.key}
                onClick={() => toggle(a.key)}
                aria-pressed={on}
                className={`group relative overflow-hidden rounded-lg border p-4 text-left transition duration-150 ${
                  on
                    ? "border-[var(--color-accent)] bg-[var(--color-accent-soft)]"
                    : "border-[var(--color-border)] bg-[var(--color-surface-2)] hover:border-[var(--color-fg-muted)]"
                }`}
              >
                {/* oversized watermark glyph — depth without noise */}
                <span
                  aria-hidden
                  className={`pointer-events-none absolute -right-2 -top-3 select-none font-mono text-6xl leading-none transition-opacity duration-200 ${
                    on
                      ? "text-[var(--color-accent)] opacity-[0.16]"
                      : "text-[var(--color-fg)] opacity-[0.05] group-hover:opacity-[0.09]"
                  }`}
                >
                  {a.glyph}
                </span>
                <span className="relative flex items-center justify-between gap-2">
                  <span className="font-mono text-sm font-medium text-[var(--color-fg)]">
                    {a.label}
                  </span>
                  <span
                    aria-hidden
                    className={`flex h-4 w-4 shrink-0 items-center justify-center rounded-full border text-[9px] leading-none transition ${
                      on
                        ? "border-[var(--color-accent)] bg-[var(--color-accent)] text-white"
                        : "border-[var(--color-border)] text-transparent"
                    }`}
                  >
                    ✓
                  </span>
                </span>
                <span className="relative mt-1.5 block text-[12px] leading-snug text-[var(--color-fg-muted)]">
                  {a.blurb}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* ── run bar ── */}
      <div className="flex flex-wrap items-center gap-3 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-2)] p-3">
        <span className="pl-1 font-mono text-[10px] uppercase tracking-widest text-[var(--color-fg-muted)]">
          Ticker
        </span>
        <input
          value={ticker}
          onChange={(e) => setTicker(e.target.value)}
          placeholder="NVDA"
          autoFocus
          className="min-w-[8rem] flex-1 rounded-md border border-[var(--color-border)] bg-[var(--color-bg)] px-3 py-2 font-mono text-sm outline-none focus:border-[var(--color-accent)]"
        />
        <button
          type="submit"
          disabled={!canRun}
          className="rounded-md border border-[var(--color-accent)] bg-[var(--color-accent-soft)] px-4 py-2 font-mono text-sm text-[var(--color-accent)] transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Run analysts →
        </button>
      </div>
    </form>
  );
}
