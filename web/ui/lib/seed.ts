import type { Artefact } from "./artefacts";
import type { SeedWatchlistItem } from "./watchlist";

export type DebateTurn = { agent: string; role: string; text: string };

export interface DebateTranscript {
  subject: string;
  turns: DebateTurn[];
  verdict: { recommendation: string; confidence: number; thesis: string };
}

export const SAMPLE_DEBATE: DebateTranscript = {
  subject: "NVDA",
  turns: [
    { agent: "Market Analyst", role: "analyst", text: "Price action shows NVDA extended 38% above its 200-day MA — momentum strong but stretched." },
    { agent: "News Analyst", role: "analyst", text: "Datacenter demand headlines remain positive; supply constraints easing into next quarter." },
    { agent: "Fundamentals Analyst", role: "analyst", text: "Forward P/E ~34x with 60%+ revenue growth; margins at record highs." },
    { agent: "Sentiment Analyst", role: "analyst", text: "Retail and institutional sentiment elevated; options skew bullish." },
    { agent: "Bull Researcher", role: "bull", text: "AI capex cycle is multi-year. Even at premium multiples the growth justifies a long." },
    { agent: "Bear Researcher", role: "bear", text: "Concentration risk is severe — a single demand air-pocket re-rates the stock 20%+ down." },
    { agent: "Bull Researcher", role: "bull", text: "Backlog visibility and pricing power blunt that air-pocket risk near term." },
    { agent: "Risk Manager", role: "risk", text: "Position-size cap warranted given volatility; stagger entries, define invalidation at the 50-day." },
  ],
  verdict: {
    recommendation: "approve",
    confidence: 0.72,
    thesis: "Constructive on NVDA into the AI capex cycle; size conservatively with a defined 50-day invalidation.",
  },
};

export const FALLBACK_STATS = {
  questions: 128,
  debates: 17,
  artefacts: 9,
  sources: 5,
};

export const SEED_ARTEFACTS: Artefact[] = [
  {
    id: "af_seed_research",
    kind: "research",
    title: "AAPL — margin & cash position overview",
    createdAt: "2026-06-20T09:12:00.000Z",
    starred: true,
    sourceCount: 4,
    payload: {
      question: "give me an overview of AAPL",
      claims: [{ text: "Gross margin held at ~45% in the latest quarter.", record_ids: ["rec_aapl_gm_2025q4"] }],
      records: [
        {
          id: "rec_aapl_gm_2025q4",
          capability: "yfinance",
          key: "fundamentals.grossMargins",
          value: 0.451,
          provenance: {
            source: "yfinance",
            locator: "https://finance.yahoo.com/quote/AAPL/financials/",
            as_of: "2025-12-31",
            detail: "Apple Inc. gross margin — FY2025 Q4 (trailing twelve months)",
          },
        },
      ],
      gaps: [],
      sources_used: ["yfinance", "filings"],
      sources_unavailable: [],
    },
  },
  {
    id: "af_seed_debate",
    kind: "debate",
    title: "NVDA — debate verdict (approve · 72%)",
    createdAt: "2026-06-22T14:40:00.000Z",
    starred: false,
    sourceCount: 0,
    payload: SAMPLE_DEBATE,
  },
  {
    id: "af_seed_clip",
    kind: "clip",
    title: "CPI.JO — key levels table",
    createdAt: "2026-06-24T11:05:00.000Z",
    starred: false,
    sourceCount: 1,
    payload: "| Indicator | Value | Signal |\n|---|---|---|\n| RSI | 58 | Neutral |\n| 50-DMA | R182 | Support |",
  },
];

export const SEED_WATCHLIST: SeedWatchlistItem[] = [
  {
    ticker: "AAPL",
    name: "Apple Inc.",
    conviction: "bull",
    note: "Margins holding; services mix improving.",
  },
  {
    ticker: "NVDA",
    name: "NVIDIA Corp.",
    conviction: "bull",
    note: "AI capex cycle; size conservatively.",
  },
  {
    ticker: "MSFT",
    name: "Microsoft Corp.",
    conviction: "watch",
    note: "",
  },
  {
    ticker: "NPN.JO",
    name: "Naspers Ltd.",
    conviction: "bear",
    note: "Discount to NAV persists.",
  },
  {
    ticker: "CPI.JO",
    name: "Capitec Bank Hldgs.",
    conviction: "watch",
    note: "",
  },
];
