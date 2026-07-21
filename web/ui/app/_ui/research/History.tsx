"use client";

import { useEffect, useState } from "react";
import { research, type ConversationSummary } from "@/lib/research";
import { SERIF } from "@/lib/research-format";

function relTime(iso: string): string {
  const then = new Date(iso).getTime();
  const s = Math.max(0, (Date.now() - then) / 1000);
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  if (s < 604800) return `${Math.floor(s / 86400)}d ago`;
  return new Date(iso).toLocaleDateString();
}

export function History({
  currentId,
  onOpen,
  onNew,
}: {
  currentId: string | null;
  onOpen: (id: string) => void;
  onNew: () => void;
}) {
  const [items, setItems] = useState<ConversationSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    research
      .listConversations()
      .then((rows) => live && setItems(rows))
      .catch(() => live && setError("Could not load history."));
    return () => {
      live = false;
    };
  }, []);

  async function remove(id: string, e: React.MouseEvent) {
    e.stopPropagation();
    setItems((xs) => (xs ?? []).filter((x) => x.id !== id));
    try {
      await research.deleteConversation(id);
    } catch {
      // best-effort; a reload will resurface it if the delete failed
    }
  }

  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-4 flex items-center justify-between">
        <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-[var(--color-accent)]">
          Conversation history
        </p>
        <button
          onClick={onNew}
          className="rounded-md border border-[var(--color-border)] px-3 py-1.5 font-mono text-[10px] uppercase tracking-wider text-[var(--color-fg-dim)] transition-colors hover:border-[var(--color-accent)] hover:text-[var(--color-fg)]"
        >
          + New chat
        </button>
      </div>

      {error && <p className="text-sm text-[var(--color-negative)]">{error}</p>}

      {items === null && !error && (
        <p className="text-sm text-[var(--color-fg-muted)]">Loading…</p>
      )}

      {items !== null && items.length === 0 && (
        <div className="rounded-[12px] border border-dashed border-[var(--color-border)] px-5 py-10 text-center">
          <p className="text-sm text-[var(--color-fg-muted)]">
            No conversations yet. Ask something in Chat — it’s saved here automatically.
          </p>
        </div>
      )}

      <ul className="space-y-2">
        {(items ?? []).map((c) => (
          <li key={c.id}>
            <button
              onClick={() => onOpen(c.id)}
              className={`group flex w-full items-center justify-between gap-3 rounded-[12px] border px-4 py-3 text-left transition-colors ${
                c.id === currentId
                  ? "border-[var(--color-accent)] bg-[var(--color-accent-soft)]"
                  : "border-[var(--color-border)] bg-[var(--color-surface)] hover:border-[var(--color-fg-muted)]"
              }`}
            >
              <div className="min-w-0">
                <p className="truncate text-sm text-[var(--color-fg)]" style={SERIF} title={c.title}>
                  {c.title}
                </p>
                <p className="mt-0.5 font-mono text-[10px] uppercase tracking-wider text-[var(--color-fg-muted)]">
                  {relTime(c.updated_at)}
                </p>
              </div>
              <span
                role="button"
                tabIndex={0}
                onClick={(e) => remove(c.id, e)}
                className="shrink-0 rounded px-2 py-1 font-mono text-[10px] uppercase tracking-wider text-[var(--color-fg-muted)] opacity-0 transition-opacity hover:text-[var(--color-negative)] group-hover:opacity-100"
              >
                Delete
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
