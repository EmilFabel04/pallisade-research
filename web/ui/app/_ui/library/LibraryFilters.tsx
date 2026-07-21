"use client";

import { useEffect, useState } from "react";
import { listTickers, type TickerCount } from "@/lib/library";
import { Input } from "../Input";

const KIND_OPTIONS: { value: string; label: string }[] = [
  { value: "", label: "All kinds" },
  { value: "final_trade_decision", label: "Final decision" },
  { value: "investment_plan", label: "Investment plan" },
  { value: "trader_investment_plan", label: "Red Team pre-mortem" },
  { value: "fundamentals_report", label: "Fundamentals" },
  { value: "news_report", label: "News" },
  { value: "sentiment_report", label: "Sentiment" },
  { value: "market_report", label: "Market" },
];

const selectClass =
  "w-full rounded-md bg-[var(--color-surface-2)] border border-[var(--color-border)] " +
  "px-3 py-2 text-sm text-[var(--color-fg)] outline-none transition " +
  "focus:border-[var(--color-accent)] focus:ring-2 focus:ring-[var(--color-accent)] focus:ring-offset-0";

export function LibraryFilters({
  ticker,
  kind,
  q,
  onChange,
}: {
  ticker: string;
  kind: string;
  q: string;
  onChange: (next: { ticker: string; kind: string; q: string }) => void;
}) {
  const [tickers, setTickers] = useState<TickerCount[]>([]);
  const [localQ, setLocalQ] = useState(q);

  useEffect(() => {
    listTickers()
      .then((res) => setTickers(res.tickers))
      .catch(() => {});
  }, []);

  function set(patch: Partial<{ ticker: string; kind: string; q: string }>) {
    onChange({ ticker, kind, q, ...patch });
  }

  return (
    <aside className="flex flex-col gap-4">
      <div>
        <label className="block font-mono text-[11px] uppercase tracking-wider text-[var(--color-fg-muted)] mb-1.5">
          Search
        </label>
        <Input
          placeholder="Title or content…"
          value={localQ}
          onChange={(e) => setLocalQ(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") set({ q: localQ });
          }}
          onBlur={() => set({ q: localQ })}
        />
      </div>

      <div>
        <label className="block font-mono text-[11px] uppercase tracking-wider text-[var(--color-fg-muted)] mb-1.5">
          Ticker
        </label>
        <select
          value={ticker}
          onChange={(e) => set({ ticker: e.target.value })}
          className={selectClass}
        >
          <option value="">All tickers</option>
          {tickers.map((t) => (
            <option key={t.ticker} value={t.ticker}>
              {t.ticker} ({t.count})
            </option>
          ))}
        </select>
      </div>

      <div>
        <label className="block font-mono text-[11px] uppercase tracking-wider text-[var(--color-fg-muted)] mb-1.5">
          Kind
        </label>
        <select
          value={kind}
          onChange={(e) => set({ kind: e.target.value })}
          className={selectClass}
        >
          {KIND_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </div>
    </aside>
  );
}
