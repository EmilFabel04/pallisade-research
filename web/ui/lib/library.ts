import { api } from "./api";

export interface LibraryListItem {
  id: string;
  run_id: string;
  ticker: string;
  kind: string;
  title: string;
  created_at: string;
  preview: string;
}

export interface LibraryListResponse {
  items: LibraryListItem[];
  next_cursor: string | null;
}

export interface LibraryDocument extends LibraryListItem {
  body_md: string;
  source_run: { id: string; ticker: string; created_at: string } | null;
}

export interface TickerCount { ticker: string; count: number; }

export function listLibrary(params: {
  ticker?: string; kind?: string; q?: string; limit?: number; cursor?: string;
} = {}): Promise<LibraryListResponse> {
  const qs = new URLSearchParams();
  if (params.ticker) qs.set("ticker", params.ticker);
  if (params.kind) qs.set("kind", params.kind);
  if (params.q) qs.set("q", params.q);
  if (params.limit) qs.set("limit", String(params.limit));
  if (params.cursor) qs.set("cursor", params.cursor);
  return api<LibraryListResponse>(`/api/library/documents?${qs}`);
}

export function getLibraryDocument(id: string): Promise<LibraryDocument> {
  return api<LibraryDocument>(`/api/library/documents/${id}`);
}

export function listTickers(): Promise<{ tickers: TickerCount[] }> {
  return api<{ tickers: TickerCount[] }>(`/api/library/tickers`);
}
