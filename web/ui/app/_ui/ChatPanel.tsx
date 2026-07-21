"use client";

import { ReactNode, useCallback, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { ChatCitation, ChatMessage, ChatSource } from "@/lib/chat";
import { Button, Emblem, EmptyState, toast } from ".";

// ─── Props ────────────────────────────────────────────────────────────────────

export interface ChatPanelProps {
  source: ChatSource;
  /** Optional header status line (e.g. "3 docs indexed"). */
  statusLine?: ReactNode;
  /** Custom empty-state node. Falls back to default if omitted. */
  emptyState?: ReactNode;
  /** Suggestion pills shown in the empty state. */
  suggestions?: string[];
  /** Textarea placeholder when the panel is ready. */
  placeholder?: string;
  /** If true the composer is disabled and shows this text in the placeholder. */
  disabledReason?: string;
  /** Callback fired after each round-trip (e.g. to refresh doc counts). */
  onRefresh?: () => void;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

interface PendingAssistant {
  text: string;
  citations: ChatCitation[];
  done: boolean;
}

function CitationChips({ items }: { items: ChatCitation[] }) {
  if (items.length === 0) return null;
  return (
    <div className="mt-3 flex flex-wrap gap-1.5">
      {items.map((c, i) => {
        const isLibrary = Boolean(c.library_doc_id);
        let label: string;
        let loc: string;
        if (isLibrary) {
          label = c.ticker ?? c.title ?? c.library_doc_id ?? "";
          loc = c.kind ?? "";
        } else {
          label = c.filename ?? "";
          loc =
            c.page_from !== null && c.page_from !== undefined
              ? `p.${c.page_from}`
              : c.sheet_name
              ? c.sheet_name
              : "";
        }
        return (
          <span
            key={c.chunk_id}
            title={`Score ${c.score.toFixed(2)}`}
            className="inline-flex items-center gap-1.5 rounded-full border border-[var(--color-border)] bg-[var(--color-surface-2)] px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-[var(--color-fg-muted)]"
          >
            <span className="text-[var(--color-accent)]">{i + 1}</span>
            <span className="text-[var(--color-fg-dim)]">{label}</span>
            {loc && <span>· {loc}</span>}
          </span>
        );
      })}
    </div>
  );
}

function TypingDots() {
  return (
    <span className="inline-flex items-center gap-1" aria-label="Assistant is typing">
      <span className="h-1.5 w-1.5 rounded-full bg-[var(--color-fg-muted)] pulse-dot" style={{ animationDelay: "0ms" }} />
      <span className="h-1.5 w-1.5 rounded-full bg-[var(--color-fg-muted)] pulse-dot" style={{ animationDelay: "150ms" }} />
      <span className="h-1.5 w-1.5 rounded-full bg-[var(--color-fg-muted)] pulse-dot" style={{ animationDelay: "300ms" }} />
    </span>
  );
}

function AssistantMessage({
  content,
  citations,
  streaming,
}: {
  content: string;
  citations: ChatCitation[];
  streaming?: boolean;
}) {
  const [copied, setCopied] = useState(false);
  async function copy() {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      toast.error("Copy failed");
    }
  }
  return (
    <div className="group flex gap-3">
      <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-[var(--color-border)] bg-[var(--color-surface-2)]">
        <Emblem size={14} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="mb-1 flex items-center gap-2">
          <span className="font-mono text-[10px] uppercase tracking-widest text-[var(--color-fg-muted)]">
            Pallisade
          </span>
          {streaming && <TypingDots />}
        </div>
        <div className="prose-research max-w-none overflow-x-auto text-sm">
          {content ? (
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
          ) : (
            <p className="text-[var(--color-fg-muted)]">Thinking…</p>
          )}
        </div>
        <CitationChips items={citations} />
        {!streaming && content && (
          <button
            onClick={copy}
            className="mt-2 font-mono text-[10px] uppercase tracking-widest text-[var(--color-fg-muted)] opacity-0 transition hover:text-[var(--color-fg)] group-hover:opacity-100"
          >
            {copied ? "Copied ✓" : "Copy"}
          </button>
        )}
      </div>
    </div>
  );
}

function UserMessage({ content }: { content: string }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[80%] rounded-2xl rounded-br-md border border-[var(--color-accent)] bg-[var(--color-accent-soft)] px-4 py-2.5 text-sm text-[var(--color-fg)]">
        <p className="whitespace-pre-wrap">{content}</p>
      </div>
    </div>
  );
}

// ─── ChatPanel ────────────────────────────────────────────────────────────────

export function ChatPanel({
  source,
  statusLine,
  emptyState,
  suggestions = [],
  placeholder = "Ask a question… (Shift+Enter for new line)",
  disabledReason,
  onRefresh,
}: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [pending, setPending] = useState<PendingAssistant | null>(null);
  const [loading, setLoading] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);
  const taRef = useRef<HTMLTextAreaElement>(null);

  const refresh = useCallback(async () => {
    try {
      const c = await source.getChat();
      setMessages(c.messages);
      onRefresh?.();
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [source, onRefresh]);

  useEffect(() => {
    setLoading(true);
    setMessages([]);
    refresh();
  }, [refresh]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, pending]);

  // Auto-grow textarea up to ~6 rows.
  useEffect(() => {
    const ta = taRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 180) + "px";
  }, [input]);

  async function send(text?: string) {
    const content = (text ?? input).trim();
    if (!content || pending || disabledReason) return;
    setInput("");
    setMessages((prev) => [
      ...prev,
      {
        id: "tmp-" + Date.now(),
        role: "user",
        content,
        citations: null,
        created_at: new Date().toISOString(),
      },
    ]);
    setPending({ text: "", citations: [], done: false });

    try {
      for await (const ev of source.streamMessage(content)) {
        if (ev.type === "token") {
          setPending((p) => (p ? { ...p, text: p.text + ev.text } : p));
        } else if (ev.type === "citations") {
          setPending((p) => (p ? { ...p, citations: ev.citations } : p));
        } else if (ev.type === "done") {
          setPending((p) => (p ? { ...p, done: true } : p));
        }
      }
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setPending(null);
      refresh();
    }
  }

  function onReset() {
    toast("Reset this conversation?", {
      description: "All messages in this thread will be deleted.",
      duration: 8000,
      action: {
        label: "Reset",
        onClick: async () => {
          try {
            await source.resetChat();
            setMessages([]);
            toast.success("Conversation reset");
          } catch (e) {
            toast.error((e as Error).message);
          }
        },
      },
    });
  }

  const composerDisabled = Boolean(disabledReason) || pending !== null;
  const activePlaceholder = disabledReason ?? placeholder;

  const defaultEmptyState = (
    <EmptyState
      icon={<Emblem size={28} />}
      title="Ask anything"
      hint="The assistant will cite the sources it draws from."
      action={
        suggestions.length > 0 ? (
          <div className="flex flex-wrap justify-center gap-2">
            {suggestions.map((s) => (
              <button
                key={s}
                disabled={composerDisabled}
                onClick={() => send(s)}
                className="rounded-full border border-[var(--color-border)] bg-[var(--color-bg)] px-3 py-1.5 text-xs text-[var(--color-fg-dim)] transition hover:border-[var(--color-accent)] hover:text-[var(--color-fg)] disabled:opacity-40"
              >
                {s}
              </button>
            ))}
          </div>
        ) : undefined
      }
    />
  );

  return (
    <section className="flex h-[calc(100vh-220px)] min-h-[520px] flex-col rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-2)]">
      {/* Header */}
      <header className="flex items-center justify-between border-b border-[var(--color-border)] px-5 py-3">
        <div className="flex items-center gap-3">
          <Emblem size={16} />
          <div>
            <p className="text-sm text-[var(--color-fg)]">Pallisade assistant</p>
            {statusLine && (
              <p className="font-mono text-[10px] uppercase tracking-widest text-[var(--color-fg-muted)]">
                {statusLine}
              </p>
            )}
          </div>
        </div>
        <button
          onClick={onReset}
          disabled={messages.length === 0}
          className="font-mono text-[10px] uppercase tracking-widest text-[var(--color-fg-muted)] underline-offset-4 transition hover:text-[var(--color-accent)] hover:underline disabled:opacity-40 disabled:no-underline disabled:hover:text-[var(--color-fg-muted)]"
        >
          Reset thread
        </button>
      </header>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 space-y-6 overflow-y-auto px-5 py-6">
        {!loading && messages.length === 0 && !pending && (emptyState ?? defaultEmptyState)}
        {messages.map((m) =>
          m.role === "user" ? (
            <UserMessage key={m.id} content={m.content} />
          ) : (
            <AssistantMessage
              key={m.id}
              content={m.content}
              citations={m.citations ?? []}
            />
          )
        )}
        {pending && (
          <AssistantMessage
            content={pending.text}
            citations={pending.citations}
            streaming
          />
        )}
      </div>

      {/* Composer */}
      <div className="border-t border-[var(--color-border)] p-3">
        <div className="flex items-end gap-2 rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)] px-3 py-2 focus-within:border-[var(--color-accent)]">
          <textarea
            ref={taRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send();
              }
            }}
            disabled={composerDisabled}
            rows={1}
            placeholder={activePlaceholder}
            className="flex-1 resize-none bg-transparent py-1.5 text-sm leading-relaxed text-[var(--color-fg)] placeholder:text-[var(--color-fg-muted)] focus:outline-none disabled:opacity-50"
          />
          <Button
            onClick={() => send()}
            disabled={composerDisabled || !input.trim()}
            className="!px-4 !py-2"
          >
            {pending ? "…" : "Send"}
          </Button>
        </div>
        <p className="mt-2 px-1 font-mono text-[10px] uppercase tracking-widest text-[var(--color-fg-muted)]">
          {pending ? "Streaming response…" : "Enter to send · Shift+Enter for newline"}
        </p>
      </div>
    </section>
  );
}
