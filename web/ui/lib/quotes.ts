// Pure, dependency-free. Keep it that way: lib/quotes.check.ts runs this file
// under `node --experimental-strip-types`, which rejects extensionless imports.

export type Conviction = "bull" | "bear" | "watch";

/** A row exactly as the backend persists it. */
export interface WatchlistRow {
  id: string;
  ticker: string;
  name: string;
  conviction: Conviction;
  note: string;
  created_at: string;
}

/** One live snapshot from GET /api/market/quotes. */
export interface Quote {
  ticker: string;
  ok: boolean;
  name?: string;
  price?: number;
  changePct?: number;
  marketCap?: string;
  pe?: number | null;
  spark?: number[];
  error?: string;
}

/** A persisted row with live market fields merged in — what the UI renders. */
export interface WatchlistItem {
  id: string;
  ticker: string;
  name: string;
  price: number;
  changePct: number;
  marketCap: string;
  pe: number;
  spark: number[];
  conviction: Conviction;
  note: string;
  addedAt: string;
}

/**
 * Merge persisted rows with live quotes. The row list drives the output: a
 * missing or ok:false quote blanks the market fields but never hides the row.
 */
export function mergeQuotes(rows: WatchlistRow[], quotes: Quote[]): WatchlistItem[] {
  const byTicker = new Map<string, Quote>();
  for (const q of quotes) {
    if (q.ok) byTicker.set(q.ticker.toUpperCase(), q);
  }

  return rows.map((row) => {
    const q = byTicker.get(row.ticker.toUpperCase());
    return {
      id: row.id,
      ticker: row.ticker,
      name: q?.name || row.name || row.ticker,
      price: q?.price ?? 0,
      changePct: q?.changePct ?? 0,
      marketCap: q?.marketCap ?? "—",
      pe: q?.pe ?? 0,
      spark: q?.spark ?? [],
      conviction: row.conviction,
      note: row.note,
      addedAt: row.created_at,
    };
  });
}
