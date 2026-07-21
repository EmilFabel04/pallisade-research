// Run: cd web/ui && node --experimental-strip-types lib/quotes.check.ts
// quotes.ts imports nothing, so it is runnable under Node's type-stripping loader.
import assert from "node:assert";
import { mergeQuotes, type Quote, type WatchlistRow } from "./quotes.ts";

const rows: WatchlistRow[] = [
  {
    id: "r1",
    ticker: "AAPL",
    name: "Apple Inc. (stale)",
    conviction: "bull",
    note: "margins",
    created_at: "2026-06-20T09:00:00.000Z",
  },
  {
    id: "r2",
    ticker: "ZZZZ",
    name: "ZZZZ",
    conviction: "watch",
    note: "",
    created_at: "2026-06-21T09:00:00.000Z",
  },
  {
    id: "r3",
    ticker: "NVDA",
    name: "NVIDIA Corp.",
    conviction: "bear",
    note: "",
    created_at: "2026-06-22T09:00:00.000Z",
  },
];

const quotes: Quote[] = [
  {
    ticker: "AAPL",
    ok: true,
    name: "Apple Inc.",
    price: 228.52,
    changePct: 0.84,
    marketCap: "3.45T",
    pe: 34.1,
    spark: [212, 228.52],
  },
  { ticker: "ZZZZ", ok: false },
];

const merged = mergeQuotes(rows, quotes);

// One item per persisted row, order preserved — never drops a row.
assert.deepStrictEqual(
  merged.map((m) => m.ticker),
  ["AAPL", "ZZZZ", "NVDA"],
);

// Live fields land on the matching row; user fields survive.
assert.strictEqual(merged[0].price, 228.52);
assert.strictEqual(merged[0].changePct, 0.84);
assert.strictEqual(merged[0].marketCap, "3.45T");
assert.strictEqual(merged[0].pe, 34.1);
assert.deepStrictEqual(merged[0].spark, [212, 228.52]);
assert.strictEqual(merged[0].conviction, "bull");
assert.strictEqual(merged[0].note, "margins");
assert.strictEqual(merged[0].addedAt, "2026-06-20T09:00:00.000Z");
assert.strictEqual(merged[0].id, "r1");

// A live name refreshes the persisted (stale) one.
assert.strictEqual(merged[0].name, "Apple Inc.");

// ok:false → row stays visible with blank market fields.
assert.strictEqual(merged[1].price, 0);
assert.strictEqual(merged[1].changePct, 0);
assert.strictEqual(merged[1].marketCap, "—");
assert.deepStrictEqual(merged[1].spark, []);
assert.strictEqual(merged[1].ticker, "ZZZZ");

// A row with no quote at all behaves like ok:false; absent quote keeps the stored name.
assert.strictEqual(merged[2].price, 0);
assert.strictEqual(merged[2].changePct, 0);
assert.strictEqual(merged[2].pe, 0);
assert.strictEqual(merged[2].name, "NVIDIA Corp.");

// Empty quote list still yields every row.
assert.strictEqual(mergeQuotes(rows, []).length, 3);
assert.deepStrictEqual(mergeQuotes([], quotes), []);

console.log("quotes.ts OK");
