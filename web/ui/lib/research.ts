// web/ui/lib/research.ts
//
// Client for the cross-source research engine (POST /api/research/ask).
// Every claim returned carries the ids of the source records that back it —
// the UI resolves those to clickable provenance (click-to-verify).

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export interface Provenance {
  source: string;
  locator: string;
  as_of: string | null; // YYYY-MM-DD or null
  detail: string;
}

export interface ResearchRecord {
  id: string;
  capability: string;
  key: string;
  value: unknown;
  provenance: Provenance;
}

export interface Claim {
  text: string;
  record_ids: string[];
}

export interface CoverageGap {
  note: string;
}

export interface CitedAnswer {
  question: string;
  claims: Claim[];
  records: ResearchRecord[];
  gaps: CoverageGap[];
  sources_used: string[];
  sources_unavailable: string[];
}

export interface ChatHistoryItem {
  role: "user" | "assistant";
  content: string;
}

/** A rendered chat turn, persisted verbatim so reopening restores the dossier. */
export interface StoredMessage {
  id: number;
  role: "user" | "assistant";
  content: string;
  answer?: CitedAnswer;
}

export interface ConversationSummary {
  id: string;
  title: string;
  updated_at: string;
}

export interface ConversationDetail extends ConversationSummary {
  messages: StoredMessage[];
}

export interface ChatQuery {
  ticker: string | null;
  capabilities: string[];
  standalone: string;
}

export interface ChatTurn {
  assistant: string; // grounded narration (may contain **markdown** bold)
  query: ChatQuery;
  answer: CitedAnswer;
}

export const research = {
  async ask(question: string): Promise<CitedAnswer> {
    const r = await fetch(`${API_BASE}/api/research/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ question }),
    });
    if (!r.ok) throw new Error(`research/ask: ${r.status} ${r.statusText}`);
    return (await r.json()) as CitedAnswer;
  },

  async chat(message: string, history: ChatHistoryItem[], deep = false): Promise<ChatTurn> {
    const r = await fetch(`${API_BASE}/api/research/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ message, history, deep }),
    });
    if (!r.ok) throw new Error(`research/chat: ${r.status} ${r.statusText}`);
    return (await r.json()) as ChatTurn;
  },

  async listConversations(): Promise<ConversationSummary[]> {
    const r = await fetch(`${API_BASE}/api/research/conversations`, { credentials: "include" });
    if (!r.ok) throw new Error(`conversations: ${r.status}`);
    return (await r.json()) as ConversationSummary[];
  },

  async getConversation(id: string): Promise<ConversationDetail> {
    const r = await fetch(`${API_BASE}/api/research/conversations/${id}`, { credentials: "include" });
    if (!r.ok) throw new Error(`conversation: ${r.status}`);
    return (await r.json()) as ConversationDetail;
  },

  async saveConversation(input: { id?: string | null; title: string; messages: StoredMessage[] }): Promise<ConversationSummary> {
    const r = await fetch(`${API_BASE}/api/research/conversations`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ id: input.id ?? null, title: input.title, messages: input.messages }),
    });
    if (!r.ok) throw new Error(`save conversation: ${r.status}`);
    return (await r.json()) as ConversationSummary;
  },

  async deleteConversation(id: string): Promise<void> {
    const r = await fetch(`${API_BASE}/api/research/conversations/${id}`, {
      method: "DELETE",
      credentials: "include",
    });
    if (!r.ok && r.status !== 404) throw new Error(`delete conversation: ${r.status}`);
  },
};
