import { api } from "./api";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export type RunStatus = "queued" | "running" | "done" | "failed";
export type Recommendation = "approve" | "decline" | "conditional";

export interface RunSummary {
  id: string;
  status: RunStatus;
  recommendation: Recommendation | null;
  confidence: number | null;
  created_at: string;
  completed_at: string | null;
}

export interface PrivateRunParams {
  entry_multiple?: number;
  hold_period_years?: number;
  target_irr?: number;
  leverage_multiple?: number;
}

export interface CreatePrivateRunBody {
  thesis?: string;
  params?: PrivateRunParams;
}

export interface AgentOutput {
  agent: string;
  summary_md: string;
  citations: { document_id: string; page: number | null; snippet: string }[];
  tokens_in: number;
  tokens_out: number;
}

export interface EvaluationResult {
  recommendation: Recommendation;
  confidence: number;
  final_thesis_md: string;
  key_risks_md: string;
  financial_summary_md: string;
  agent_outputs: AgentOutput[];
  tokens_in: number;
  tokens_out: number;
  cost_usd: number;
}

export interface RunDetail {
  run: {
    id: string;
    status: RunStatus;
    thesis: string | null;
    params: PrivateRunParams | null;
    current_node: string | null;
    artifacts_root_key: string;
    error_message: string | null;
    created_at: string;
    completed_at: string | null;
  };
  result: EvaluationResult | null;
}


export async function createRun(dealId: string, body: CreatePrivateRunBody): Promise<{ run_id: string }> {
  const r = await fetch(`${API_BASE}/api/deals/${dealId}/runs`, {
    method: "POST", credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (r.status === 409) {
    const detail = (await r.json()).detail as string;
    throw new Error(detail);
  }
  if (!r.ok) throw new Error(`createRun failed: ${r.status}`);
  return r.json();
}


export async function listRuns(dealId: string): Promise<{ runs: RunSummary[] }> {
  const r = await fetch(`${API_BASE}/api/deals/${dealId}/runs`, { credentials: "include" });
  if (!r.ok) throw new Error(`listRuns failed: ${r.status}`);
  return r.json();
}


export async function getRun(dealId: string, runId: string): Promise<RunDetail> {
  const r = await fetch(`${API_BASE}/api/deals/${dealId}/runs/${runId}`, { credentials: "include" });
  if (!r.ok) throw new Error(`getRun failed: ${r.status}`);
  return r.json();
}


export interface PublicRunSummary {
  id: string;
  ticker: string;
  trade_date: string | null;
  status: string;
  created_at: string;
}

export function listPublicRuns(): Promise<{ runs: PublicRunSummary[] }> {
  return api<{ runs: PublicRunSummary[] }>(`/api/runs`);
}


export interface RecentPrivateRun {
  run_id: string;
  deal_id: string;
  deal_name: string;
  target_company: string;
  status: RunStatus;
  recommendation: Recommendation | null;
  confidence: number | null;
  created_at: string;
  completed_at: string | null;
}

export function listRecentPrivateRuns(limit = 5): Promise<{ runs: RecentPrivateRun[] }> {
  return api<{ runs: RecentPrivateRun[] }>(`/api/private-runs/recent?limit=${limit}`);
}
