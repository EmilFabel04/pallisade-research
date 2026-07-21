import { api } from "./api";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export type DebateStatus = "queued" | "running" | "done" | "error" | "failed";

export interface LaneMeta {
  key: string;
  agent: string;
  role: string;
  /** verdict lane renders as the final decision card, not a normal lane */
  verdict?: boolean;
}

/**
 * Canonical lane order — mirrors REPORT_KEYS on the API.
 * INVARIANT: the single verdict lane (`final_trade_decision`) must stay LAST.
 * LaneBoard.laneStatus operates on whatever (already verdict-filtered) lane
 * subset it is given as a parameter, so it no longer indexes this array
 * directly. The "verdict lane stays last" ordering here only matters for the
 * default `lanes = REPORT_LANES` call path, so that the Debate page's default
 * (all-lanes) rendering stays byte-identical.
 */
export const REPORT_LANES: LaneMeta[] = [
  { key: "market_report", agent: "Market Analyst", role: "technicals" },
  { key: "sentiment_report", agent: "Social Analyst", role: "sentiment" },
  { key: "news_report", agent: "News Analyst", role: "catalysts" },
  { key: "fundamentals_report", agent: "Fundamentals", role: "valuation" },
  { key: "investment_plan", agent: "Research Manager", role: "bull vs bear" },
  { key: "trader_investment_plan", agent: "Red Team", role: "pre-mortem" },
  { key: "final_trade_decision", agent: "Portfolio Manager", role: "verdict", verdict: true },
];

const LANE_BY_KEY: Record<string, LaneMeta> = Object.fromEntries(
  REPORT_LANES.map((l) => [l.key, l])
);

export function reportKeyToLane(key: string): LaneMeta | null {
  return LANE_BY_KEY[key] ?? null;
}

export interface DebateRunDetail {
  id: string;
  ticker: string;
  trade_date: string | null;
  asset_type: string | null;
  analysts: string[] | null;
  status: DebateStatus;
  created_at: string;
  reports: Record<string, string>;
  final_state: Record<string, string> | null;
  error: string | null;
}

export interface DebateRunSummary {
  id: string;
  ticker: string;
  trade_date: string | null;
  analysts: string[] | null;
  status: DebateStatus;
  created_at: string;
}

/** Today as YYYY-MM-DD in local time (the engine only needs a date string). */
function today(): string {
  const d = new Date();
  const z = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${z(d.getMonth() + 1)}-${z(d.getDate())}`;
}

export function createDebateRun(input: {
  ticker: string;
  rounds: number;
  analysts?: string[];
  analystsOnly?: boolean;
}): Promise<{ run_id: string }> {
  return api<{ run_id: string }>(`/api/runs`, {
    method: "POST",
    body: JSON.stringify({
      ticker: input.ticker.trim().toUpperCase(),
      trade_date: today(),
      max_debate_rounds: input.rounds,
      ...(input.analysts ? { analysts: input.analysts } : {}),
      analysts_only: input.analystsOnly ?? false,
    }),
  });
}

export function getDebateRun(id: string): Promise<DebateRunDetail> {
  return api<DebateRunDetail>(`/api/runs/${id}`);
}

export function listDebateRuns(
  kind?: "analysts" | "debate",
): Promise<{ runs: DebateRunSummary[] }> {
  const q = kind ? `?kind=${kind}` : "";
  return api<{ runs: DebateRunSummary[] }>(`/api/runs${q}`);
}

export const STREAM_URL = (id: string) => `${API_BASE}/api/runs/${id}/stream`;

export type DebatePhase = "invest" | "risk";

/** Invest speakers render as a two-sided chat. Risk speakers are stored but
 *  NOT rendered this slice (spec §D5). */
export type DebateSpeaker = "bull" | "bear" | "aggressive" | "conservative" | "neutral";

export interface DebateTurn {
  /** Monotonic per-run event seq — also the dedupe key. */
  seq: number;
  phase: DebatePhase;
  speaker: DebateSpeaker;
  round: number;
  text: string;
  ts?: string;
}

export const SPEAKER_META: Record<string, { label: string; side: "left" | "right" }> = {
  bull: { label: "Bull", side: "left" },
  bear: { label: "Bear", side: "right" },
};

/** One-line preview of a markdown report body for collapsed turns/lanes.
 *  Uses the first non-empty line — which, for our rendered reports, is the
 *  rating/verdict header (e.g. "**Recommendation**: Overweight"). */
export function summarize(markdown: string, max = 120): string {
  const line =
    markdown
      .split("\n")
      .map((l) => l.trim())
      .find((l) => l.length > 0) ?? "";
  const plain = line.replace(/[*_`#>]/g, "").trim();
  return plain.length > max ? plain.slice(0, max - 1).trimEnd() + "…" : plain;
}

/** First `**Takeaway**: <sentence>` line, or null. */
export function extractTakeaway(md: string): string | null {
  for (const line of md.split("\n")) {
    const m = line.match(/^\s*\*\*Takeaway\*\*:\s*(.+)$/);
    if (m) return m[1].trim();
  }
  return null;
}

/** Every `**Label**: value` line collapsed into a lookup. */
export function parseFields(md: string): Record<string, string> {
  const out: Record<string, string> = {};
  for (const line of md.split("\n")) {
    const m = line.match(/^\s*\*\*(.+?)\*\*:\s*(.+)$/);
    if (m) out[m[1].trim()] = m[2].trim();
  }
  return out;
}

/** Badge tone for a 5-tier rating. */
export function ratingTone(rating: string): "ok" | "neutral" | "warn" | "err" {
  switch (rating.trim().toLowerCase()) {
    case "buy":
    case "overweight":
      return "ok";
    case "underweight":
      return "warn";
    case "sell":
      return "err";
    default:
      return "neutral";
  }
}
