import { api } from "./api";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

// ChatCitation is intentionally loose so it works for both deal-shaped and
// library-shaped responses. Discriminate at runtime via `library_doc_id`.
export interface ChatCitation {
  chunk_id: string;
  score: number;
  // deal-shaped fields
  document_id?: string;
  filename?: string;
  page_from?: number | null;
  page_to?: number | null;
  sheet_name?: string | null;
  // library-shaped fields
  library_doc_id?: string;
  kind?: string;
  ticker?: string;
  title?: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations: ChatCitation[] | null;
  created_at: string;
}

export interface ChatResponse {
  conversation_id: string;
  title: string | null;
  messages: ChatMessage[];
}

export type ChatStreamEvent =
  | { type: "token"; text: string }
  | { type: "citations"; citations: ChatCitation[] }
  | { type: "done" };

// ─── Generic SSE streaming helper ────────────────────────────────────────────

async function* streamSSE(
  url: string,
  body: unknown,
): AsyncGenerator<ChatStreamEvent> {
  const res = await fetch(url, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok || !res.body) throw new Error(`stream failed: ${res.status}`);
  const reader = res.body.getReader();
  const dec = new TextDecoder();
  let buf = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    let idx: number;
    while ((idx = buf.indexOf("\n\n")) >= 0) {
      const block = buf.slice(0, idx);
      buf = buf.slice(idx + 2);
      const line = block.split("\n").find((l) => l.startsWith("data: "));
      if (!line) continue;
      yield JSON.parse(line.slice(6)) as ChatStreamEvent;
    }
  }
}

// ─── ChatSource interface ─────────────────────────────────────────────────────

export interface ChatSource {
  getChat(): Promise<ChatResponse>;
  resetChat(): Promise<void>;
  streamMessage(content: string): AsyncGenerator<ChatStreamEvent>;
}

// ─── Deal chat source ─────────────────────────────────────────────────────────

export function dealChatSource(dealId: string): ChatSource {
  return {
    getChat: () => api<ChatResponse>(`/api/deals/${dealId}/chat`),
    resetChat: () => api<void>(`/api/deals/${dealId}/chat`, { method: "DELETE" }),
    streamMessage: (content) =>
      streamSSE(`${API_BASE}/api/deals/${dealId}/chat/messages`, { content }),
  };
}

// ─── Library-doc chat source ──────────────────────────────────────────────────

export function libraryDocChatSource(docId: string): ChatSource {
  return {
    getChat: () => api<ChatResponse>(`/api/library/documents/${docId}/chat`),
    resetChat: () => api<void>(`/api/library/documents/${docId}/chat`, { method: "DELETE" }),
    streamMessage: (content) =>
      streamSSE(`${API_BASE}/api/library/documents/${docId}/chat/messages`, { content }),
  };
}

// ─── Global library chat source ───────────────────────────────────────────────

export function globalChatSource(): ChatSource {
  return {
    getChat: () => api<ChatResponse>(`/api/chat/global`),
    resetChat: () => api<void>(`/api/chat/global`, { method: "DELETE" }),
    streamMessage: (content) =>
      streamSSE(`${API_BASE}/api/chat/global/messages`, { content }),
  };
}

// ─── Deal-specific convenience wrappers (kept for backward compat) ────────────

export function getChat(dealId: string): Promise<ChatResponse> {
  return api<ChatResponse>(`/api/deals/${dealId}/chat`);
}

export function resetChat(dealId: string): Promise<void> {
  return api<void>(`/api/deals/${dealId}/chat`, { method: "DELETE" });
}

export async function* streamChatMessage(
  dealId: string,
  content: string,
): AsyncGenerator<ChatStreamEvent> {
  yield* streamSSE(`${API_BASE}/api/deals/${dealId}/chat/messages`, { content });
}
