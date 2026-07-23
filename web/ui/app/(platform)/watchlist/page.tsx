"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Plus, RefreshCw } from "lucide-react";
import { PageHeader, EmptyState, IconButton } from "@/app/_ui";
import { useWatchlist, ensureWatchlistSeeded } from "@/lib/watchlist";
import { ApiError } from "@/lib/api";
import { SEED_WATCHLIST } from "@/lib/seed";
import { WatchlistRow } from "./_ui/WatchlistRow";

export default function WatchlistPage() {
  useEffect(() => {
    void ensureWatchlistSeeded(SEED_WATCHLIST);
  }, []);

  const { items, loading, quotesFailed, listFailed, add, remove, update, refresh, reload } =
    useWatchlist();
  const [symbol, setSymbol] = useState("");
  const [addError, setAddError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const router = useRouter();

  async function addTicker() {
    if (busy) return; // ignore a second Enter/submit while one is already in flight
    const t = symbol.trim().toUpperCase();
    if (!t) return;
    setAddError(null);
    setBusy(true);
    try {
      await add(t);
      setSymbol(""); // only clear on success — a rejected symbol stays editable
    } catch (err) {
      if (err instanceof ApiError && err.status === 422) {
        setAddError(`Couldn't find the symbol "${t}".`);
      } else if (err instanceof ApiError && err.status === 409) {
        setAddError(`${t} is already on your watchlist.`);
      } else {
        setAddError(`Couldn't add ${t}. Try again.`);
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHeader eyebrow="Markets" title="Watchlist">
        <div className="flex items-center gap-2">
          <IconButton
            icon={RefreshCw}
            label="Refresh quotes"
            variant="ghost"
            size="sm"
            onClick={() => void refresh()}
          />
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void addTicker();
            }}
            className="flex items-center gap-2"
          >
            <input
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              placeholder="Add ticker…"
              aria-label="Add ticker"
              className="w-36 rounded-md border border-[var(--color-border)] bg-[var(--color-bg)] px-3 py-1.5 font-mono text-xs uppercase text-[var(--color-fg)] placeholder:text-[var(--color-fg-muted)] transition-colors focus:border-[var(--color-accent)] focus:outline-none"
            />
            <IconButton
              type="submit"
              icon={Plus}
              label={busy ? "Adding ticker…" : "Add ticker"}
              variant="primary"
              size="sm"
              disabled={busy}
            />
          </form>
        </div>
      </PageHeader>

      {listFailed && (
        <div
          role="alert"
          className="mb-4 flex items-center gap-3 rounded-md border border-[var(--color-negative)] px-3 py-2 font-mono text-xs text-[var(--color-negative)]"
        >
          <span>Couldn&apos;t reach the server. Showing the last loaded list.</span>
          <button
            type="button"
            onClick={() => void reload()}
            className="underline transition-colors hover:text-[var(--color-fg)]"
          >
            Retry
          </button>
        </div>
      )}

      {addError && (
        <div
          role="alert"
          className="mb-4 rounded-md border border-[var(--color-negative)] px-3 py-2 font-mono text-xs text-[var(--color-negative)]"
        >
          {addError}
        </div>
      )}

      {quotesFailed && (
        <div
          role="status"
          className="mb-4 flex items-center gap-3 rounded-md border border-[var(--color-border)] px-3 py-2 font-mono text-xs text-[var(--color-fg-muted)]"
        >
          <span>Prices unavailable right now.</span>
          <button
            type="button"
            onClick={() => void refresh()}
            className="underline transition-colors hover:text-[var(--color-fg)]"
          >
            Retry
          </button>
        </div>
      )}

      {loading ? (
        <div className="elevated rounded-lg border border-[var(--color-border)] px-4 py-8 text-center font-mono text-xs text-[var(--color-fg-muted)]">
          Loading watchlist…
        </div>
      ) : items.length === 0 ? (
        // A failed list fetch already explains itself via the banner above —
        // don't also claim the watchlist is empty when we simply couldn't
        // reach the server to find out.
        listFailed ? null : (
          <EmptyState
            title="No tickers yet"
            hint="Add a symbol above to start your watchlist."
          />
        )
      ) : (
        <div className="elevated overflow-hidden rounded-lg border border-[var(--color-border)]">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--color-border)] text-left font-mono text-[10px] uppercase tracking-widest text-[var(--color-fg-muted)]">
                <th className="px-4 py-2.5">Ticker</th>
                <th className="px-4 py-2.5 text-right">Price</th>
                <th className="px-4 py-2.5 text-right">Chg %</th>
                <th className="px-4 py-2.5 text-right">Mkt Cap</th>
                <th className="px-4 py-2.5 text-right">P/E</th>
                <th className="px-4 py-2.5">Trend</th>
                <th className="px-4 py-2.5">Conviction</th>
                <th className="px-4 py-2.5">Coverage</th>
                <th className="px-4 py-2.5">Note</th>
                <th className="px-4 py-2.5 text-right">Added</th>
                <th className="px-4 py-2.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((it) => (
                <WatchlistRow
                  key={it.id}
                  item={it}
                  onResearch={() =>
                    router.push(`/research?q=${encodeURIComponent(`overview of ${it.ticker}`)}`)
                  }
                  onDebate={() =>
                    router.push(`/debate?subject=${encodeURIComponent(it.ticker)}`)
                  }
                  onRemove={() => void remove(it.id)}
                  onUpdate={(patch) => void update(it.id, patch)}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
