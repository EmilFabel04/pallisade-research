"use client";

import { useState } from "react";

const ROUND_OPTIONS = [1, 2, 3];

export function Launchpad({
  initialTicker = "",
  onRun,
}: {
  initialTicker?: string;
  onRun: (input: { ticker: string; rounds: number }) => void;
}) {
  const [ticker, setTicker] = useState(initialTicker);
  const [rounds, setRounds] = useState(2);

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const t = ticker.trim();
    if (!t) return;
    onRun({ ticker: t, rounds });
  }

  return (
    <form
      onSubmit={submit}
      className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-5"
    >
      <label className="mb-2 block font-mono text-[10px] uppercase tracking-widest text-[var(--color-fg-muted)]">
        Ticker
      </label>
      <div className="flex flex-wrap items-center gap-3">
        <input
          value={ticker}
          onChange={(e) => setTicker(e.target.value)}
          placeholder="NVDA"
          autoFocus
          className="flex-1 min-w-[10rem] rounded-md border border-[var(--color-border)] bg-[var(--color-bg)] px-3 py-2 font-mono text-sm outline-none focus:border-[var(--color-accent)]"
        />
        <label className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-wider text-[var(--color-fg-muted)]">
          Rounds
          <select
            value={rounds}
            onChange={(e) => setRounds(Number(e.target.value))}
            className="rounded-md border border-[var(--color-border)] bg-[var(--color-bg)] px-2 py-2 font-mono text-sm outline-none focus:border-[var(--color-accent)]"
          >
            {ROUND_OPTIONS.map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </label>
        <button
          type="submit"
          disabled={!ticker.trim()}
          className="rounded-md border border-[var(--color-accent)] bg-[var(--color-accent-soft)] px-4 py-2 font-mono text-sm text-[var(--color-accent)] transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Run debate →
        </button>
      </div>
    </form>
  );
}
