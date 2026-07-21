"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api";
import {
  mergeQuotes,
  type Conviction,
  type Quote,
  type WatchlistItem,
  type WatchlistRow,
} from "./quotes";

export type { Conviction, WatchlistItem, WatchlistRow, Quote };

/** Guard flag: seeding runs once per device and never again after a manual clear. */
export const SEED_KEY = "pallisade.watchlist.seeded.v2";

/** The demo-seed shape — user fields only; market data is fetched live. */
export interface SeedWatchlistItem {
  ticker: string;
  name: string;
  conviction: Conviction;
  note: string;
}

function listRows(): Promise<{ items: WatchlistRow[] }> {
  return api<{ items: WatchlistRow[] }>("/api/watchlist");
}

function fetchQuotes(tickers: string[]): Promise<{ quotes: Quote[] }> {
  if (tickers.length === 0) return Promise.resolve({ quotes: [] });
  const symbols = encodeURIComponent(tickers.join(","));
  return api<{ quotes: Quote[] }>(`/api/market/quotes?symbols=${symbols}`);
}

export function useWatchlist() {
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [quotesFailed, setQuotesFailed] = useState(false);
  const [listFailed, setListFailed] = useState(false);
  const rowsRef = useRef<WatchlistRow[]>([]);

  /** Re-pull quotes for the rows we already hold. Keeps rows on failure. */
  const refresh = useCallback(async () => {
    const rows = rowsRef.current;
    if (rows.length === 0) {
      setItems([]);
      setQuotesFailed(false); // no rows left: any stale "prices unavailable" banner no longer applies
      return;
    }
    try {
      const { quotes } = await fetchQuotes(rows.map((r) => r.ticker));
      setItems(mergeQuotes(rows, quotes));
      setQuotesFailed(false);
    } catch {
      // Prices unreachable: still render the persisted list.
      setQuotesFailed(true);
      setItems((prev) => (prev.length > 0 ? prev : mergeQuotes(rows, [])));
    }
  }, []);

  /** Re-pull the persisted list, then its quotes. */
  const reload = useCallback(async () => {
    try {
      const { items: rows } = await listRows();
      rowsRef.current = rows;
      setListFailed(false);
      // Seed the merged list from whatever market data we already hold, rather
      // than blanking it: if refresh() below fails (quotes endpoint down), the
      // last-known price stays on screen instead of resetting to 0/"—". Read
      // current items via the setItems updater (not the `items` closure) so
      // reload stays referentially stable and the mount effect doesn't loop.
      setItems((prev) => {
        const byTicker = new Map(prev.map((i) => [i.ticker.toUpperCase(), i]));
        const carried: Quote[] = [];
        for (const row of rows) {
          const prior = byTicker.get(row.ticker.toUpperCase());
          if (prior && prior.price > 0) {
            carried.push({
              ticker: prior.ticker,
              ok: true,
              name: prior.name,
              price: prior.price,
              changePct: prior.changePct,
              marketCap: prior.marketCap,
              pe: prior.pe,
              spark: prior.spark,
            });
          }
        }
        // Rows with no prior market data (genuinely new) fall through to
        // mergeQuotes' blank defaults, which is correct: they have no price yet.
        return mergeQuotes(rows, carried);
      });
      await refresh();
    } catch {
      // List fetch failed: leave rowsRef/items exactly as they are — a
      // transient backend blip should never masquerade as an empty
      // watchlist. Flag it instead; page.tsx renders a banner and the
      // items.length === 0 empty-state check yields to that banner.
      setListFailed(true);
    } finally {
      setLoading(false);
    }
  }, [refresh]);

  useEffect(() => {
    void reload();
    const onChange = () => void reload();
    window.addEventListener("watchlist:changed", onChange);
    return () => window.removeEventListener("watchlist:changed", onChange);
  }, [reload]);

  const add = useCallback(
    async (ticker: string, conviction: Conviction = "watch", note = "") => {
      await api<WatchlistRow>("/api/watchlist", {
        method: "POST",
        body: JSON.stringify({ ticker: ticker.trim().toUpperCase(), conviction, note }),
      });
      await reload();
    },
    [reload],
  );

  const remove = useCallback(
    async (id: string) => {
      // Optimistic: drop it locally, then confirm with the server.
      rowsRef.current = rowsRef.current.filter((r) => r.id !== id);
      setItems((prev) => prev.filter((i) => i.id !== id));
      try {
        await api<void>(`/api/watchlist/${id}`, { method: "DELETE" });
      } catch {
        // Swallow: unlike add's ApiError (deliberately surfaced for inline
        // 422/409 messages), a failed delete has no UI affordance to react to —
        // the row was already dropped optimistically. reload() below
        // reconciles against the server either way, so a failed delete
        // honestly brings the row back.
      } finally {
        await reload();
      }
    },
    [reload],
  );

  const update = useCallback(
    async (id: string, patch: { conviction?: Conviction; note?: string }) => {
      // Optimistic: the row edits feel instant; the server is the tiebreak.
      rowsRef.current = rowsRef.current.map((r) => (r.id === id ? { ...r, ...patch } : r));
      setItems((prev) => prev.map((i) => (i.id === id ? { ...i, ...patch } : i)));
      try {
        await api<WatchlistRow>(`/api/watchlist/${id}`, {
          method: "PATCH",
          body: JSON.stringify(patch),
        });
      } catch {
        await reload(); // reconcile away a failed optimistic edit
      }
    },
    [reload],
  );

  return { items, loading, quotesFailed, listFailed, add, remove, update, refresh, reload };
}

/**
 * Seed the demo tickers into the backend once per device. The guard flag is set
 * before the POSTs resolve so a user who then empties the list is never
 * re-seeded on the next load.
 */
export async function ensureWatchlistSeeded(seed: SeedWatchlistItem[]): Promise<void> {
  if (typeof window === "undefined") return;
  if (window.localStorage.getItem(SEED_KEY) !== null) return;
  window.localStorage.setItem(SEED_KEY, "1");

  for (const s of seed) {
    try {
      await api<WatchlistRow>("/api/watchlist", {
        method: "POST",
        body: JSON.stringify({ ticker: s.ticker, conviction: s.conviction, note: s.note }),
      });
    } catch {
      // Seeding is best-effort: 409 (already there) and 422 (yfinance can't
      // resolve it) are benign, and a network-level failure (fetch throws a
      // bare TypeError, not an ApiError, when the API is unreachable) is just
      // as benign here — swallow everything so one failed ticker doesn't
      // abort the rest of the loop and nothing escapes as an unhandled
      // rejection (this function's only caller never attaches a .catch()).
    }
  }
}
