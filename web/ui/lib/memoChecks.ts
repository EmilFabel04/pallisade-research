import { api } from "@/lib/api";

export type CheckStatus = "queued" | "running" | "done" | "failed";
export type Verdict = "match" | "mismatch" | "stale" | "unsupported";

export interface MemoCheck {
  id: string;
  org_id: string;
  memo_document_id: string | null;
  memo_text: string;
  backing_document_ids: string[];
  scope: "attached" | "folder" | "both";
  status: CheckStatus;
  created_at: string;
}

export interface MemoClaimResult {
  claim_text: string;
  claim_value: string;
  verdict: Verdict;
  source_document_id: string | null;
  locator: string | null;
  source_value: string | null;
  source_as_of: string | null;
  tier: string;
  rationale: string | null;
  char_start: number | null;
  char_end: number | null;
}

export interface MemoCheckDetail {
  check: MemoCheck;
  results: MemoClaimResult[];
}

export const createMemoCheck = (body: {
  memo_text: string;
  backing_document_ids?: string[];
  scope?: "attached" | "folder" | "both";
}) =>
  api<MemoCheck>("/api/memo-checks", {
    method: "POST",
    body: JSON.stringify({
      memo_text: body.memo_text,
      backing_document_ids: body.backing_document_ids ?? [],
      scope: body.scope ?? "folder",
    }),
  });

export const getMemoCheck = (id: string) =>
  api<MemoCheckDetail>(`/api/memo-checks/${id}`);

export const listMemoChecks = () =>
  api<{ checks: MemoCheck[] }>("/api/memo-checks");
