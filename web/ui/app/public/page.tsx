"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";
import { Button, Field, Input } from "../_ui";

const ALL_ANALYSTS = [
  { id: "market", label: "Market", hint: "MACD · RSI · price action" },
  { id: "social", label: "Sentiment", hint: "news · social · Reddit" },
  { id: "news", label: "News", hint: "global headlines · macro" },
  { id: "fundamentals", label: "Fundamentals", hint: "financials · filings" },
];

const ASSET_TYPES = ["stock", "etf", "crypto"] as const;
type AssetType = (typeof ASSET_TYPES)[number];

export default function NewRunPage() {
  const router = useRouter();
  const [ticker, setTicker] = useState("NVDA");
  const [tradeDate, setTradeDate] = useState(
    new Date().toISOString().slice(0, 10),
  );
  const [analysts, setAnalysts] = useState<string[]>([
    "market",
    "social",
    "news",
    "fundamentals",
  ]);
  const [assetType, setAssetType] = useState<AssetType>("stock");
  const [debate, setDebate] = useState(1);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function toggleAnalyst(id: string) {
    setAnalysts((curr) =>
      curr.includes(id) ? curr.filter((a) => a !== id) : [...curr, id],
    );
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (analysts.length === 0) {
      setError("Select at least one analyst.");
      return;
    }
    setSubmitting(true);
    try {
      const json = await api<{ run_id: string }>("/api/runs", {
        method: "POST",
        body: JSON.stringify({
          ticker,
          trade_date: tradeDate,
          analysts,
          asset_type: assetType,
          max_debate_rounds: debate,
        }),
      });
      router.push(`/public/runs/${json.run_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setSubmitting(false);
    }
  }

  return (
    <main>
      <section className="mb-12 max-w-3xl">
        <h1 className="text-3xl font-medium tracking-tight">
          New research dossier
        </h1>
        <p className="mt-3 text-[var(--color-fg-dim)] max-w-2xl">
          Compose a multi-agent research dossier for a single ticker. The system
          will run analyst, debate, and risk-review agents and surface their
          reports below as they complete.
        </p>
      </section>

      <form onSubmit={submit} className="grid grid-cols-12 gap-6">
        <div className="col-span-12 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-6">
          <SectionTitle index="01" title="Target" />
          <div className="mt-5 grid grid-cols-12 gap-4">
            <Field className="col-span-7" label="Ticker">
              <Input
                value={ticker}
                onChange={(e) => setTicker(e.target.value.toUpperCase())}
                required
                maxLength={20}
                className="font-mono uppercase tracking-wider text-2xl"
                placeholder="NVDA"
              />
            </Field>
            <Field className="col-span-5" label="Asset type">
              <div className="grid grid-cols-3 gap-2">
                {ASSET_TYPES.map((t) => (
                  <button
                    type="button"
                    key={t}
                    onClick={() => setAssetType(t)}
                    className={`rounded-md px-3 py-2 font-mono text-xs uppercase tracking-wider transition border ${
                      assetType === t
                        ? "border-[var(--color-accent)] bg-[var(--color-accent-soft)] text-[var(--color-fg)]"
                        : "border-[var(--color-border)] bg-[var(--color-surface-2)] text-[var(--color-fg-dim)] hover:border-[var(--color-fg-muted)]"
                    }`}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </Field>
            <Field className="col-span-12" label="Trade date">
              <Input
                type="date"
                value={tradeDate}
                onChange={(e) => setTradeDate(e.target.value)}
                required
                className="font-mono"
              />
            </Field>
          </div>

          <div className="my-8 border-t border-[var(--color-border)]" />

          <SectionTitle index="02" title="Analysts" />
          <p className="mt-2 text-sm text-[var(--color-fg-dim)]">
            Each analyst produces an independent report. Researchers and risk
            reviewers always run after.
          </p>
          <div className="mt-5 grid grid-cols-2 gap-3">
            {ALL_ANALYSTS.map((a) => (
              <button
                type="button"
                key={a.id}
                onClick={() => toggleAnalyst(a.id)}
                className={`text-left rounded-md border p-3 transition ${
                  analysts.includes(a.id)
                    ? "border-[var(--color-accent)] bg-[var(--color-accent-soft)]"
                    : "border-[var(--color-border)] hover:border-[var(--color-fg-muted)]"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-sm">{a.label}</span>
                  <span
                    className={`h-2 w-2 rounded-full ${
                      analysts.includes(a.id)
                        ? "bg-[var(--color-accent)]"
                        : "bg-[var(--color-fg-muted)]"
                    }`}
                  />
                </div>
                <div className="mt-1 text-xs text-[var(--color-fg-muted)]">
                  {a.hint}
                </div>
              </button>
            ))}
          </div>

          <div className="my-8 border-t border-[var(--color-border)]" />

          <SectionTitle index="03" title="Debate" />
          <div className="mt-5">
            <Field label={`Debate rounds — ${debate}`}>
              <input
                type="range"
                min={1}
                max={5}
                value={debate}
                onChange={(e) => setDebate(parseInt(e.target.value))}
                className="w-full accent-[var(--color-accent)]"
              />
            </Field>
          </div>
        </div>

        <div className="col-span-12 flex items-center justify-between">
          <div className="text-xs text-[var(--color-fg-muted)]">
            {analysts.length} analyst{analysts.length === 1 ? "" : "s"} ·{" "}
            {debate} debate round{debate === 1 ? "" : "s"}
          </div>
          <div className="flex items-center gap-4">
            {error && (
              <span className="font-mono text-sm text-[var(--color-accent)]">
                {error}
              </span>
            )}
            <Button type="submit" disabled={submitting} variant="primary">
              {submitting ? "Dispatching…" : "Run dossier →"}
            </Button>
          </div>
        </div>
      </form>
    </main>
  );
}

function SectionTitle({ index, title }: { index: string; title: string }) {
  return (
    <div className="flex items-baseline gap-3">
      <span className="font-mono text-xs text-[var(--color-fg-muted)]">
        {index}
      </span>
      <h2 className="font-mono text-sm tracking-wider uppercase text-[var(--color-fg-dim)]">
        {title}
      </h2>
    </div>
  );
}
