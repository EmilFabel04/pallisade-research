"use client";

import { useEffect, useRef, useState } from "react";
import { research, type ChatHistoryItem, type CitedAnswer } from "@/lib/research";
import { useRevealedText } from "@/lib/useRevealedText";
import { ThinkingSequence } from "./_ui/ThinkingSequence";
import { SERIF, inlineSegments, stripBlockMarkdown } from "@/lib/research-format";
import { Artifact } from "@/app/_ui/research/Artifact";
import { History } from "@/app/_ui/research/History";
import { saveArtefact } from "@/lib/artefacts";
import { toast, Segmented, Eyebrow, Button } from "@/app/_ui";

type View = "chat" | "history";

interface Msg {
  id: number;
  role: "user" | "assistant";
  content: string;
  answer?: CitedAnswer;
}

const SUGGESTIONS = [
  "give me an overview of AAPL",
  "is NPN.JO worth holding?",
  "what about its profit margin?",
  "overview of CPI.JO",
];

function Narration({ text }: { text: string }) {
  return (
    <div className="space-y-2 text-[14px] leading-relaxed text-[var(--color-fg-dim)]">
      {text.split("\n").map((line, i) =>
        line.trim() ? (
          <p key={i}>
            {inlineSegments(stripBlockMarkdown(line)).map((s, j) =>
              s.t === "bold" ? (
                <strong key={j} className="font-semibold text-[var(--color-fg)]">
                  {s.v}
                </strong>
              ) : s.t === "cite" ? (
                <span
                  key={j}
                  className="mx-0.5 rounded bg-[var(--color-accent-soft)] px-1 font-mono text-[11px] uppercase tracking-wide text-[var(--color-fg-dim)]"
                >
                  {s.v}
                </span>
              ) : (
                <span key={j}>{s.v}</span>
              ),
            )}
          </p>
        ) : null,
      )}
    </div>
  );
}

function AssistantNarration({ text, reveal }: { text: string; reveal: boolean }) {
  const { shown } = useRevealedText(text, { enabled: reveal });
  return <Narration text={reveal ? shown : text} />;
}

export default function ResearchDashboard() {
  const [view, setView] = useState<View>("chat");
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [pending, setPending] = useState(false);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [savedIds, setSavedIds] = useState<Set<number>>(new Set());
  const [convId, setConvId] = useState<string | null>(null);
  const [deep, setDeep] = useState(false);
  const idRef = useRef(0);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const q = new URLSearchParams(window.location.search).get("q");
    if (q) setInput(q);
  }, []);

  // Auto-save the conversation whenever a completed answer turn lands: create it
  // on the first turn (capturing the returned id), update it on every turn after.
  useEffect(() => {
    if (pending) return;
    const last = messages[messages.length - 1];
    if (!last || last.role !== "assistant" || !last.answer) return;
    const title = (messages.find((m) => m.role === "user")?.content ?? "Research").slice(0, 200);
    let cancelled = false;
    research
      .saveConversation({ id: convId, title, messages })
      .then((s) => {
        if (!cancelled && !convId) setConvId(s.id);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [messages, pending]);

  function newChat() {
    setMessages([]);
    setConvId(null);
    setActiveId(null);
    setSavedIds(new Set());
    idRef.current = 0;
    setView("chat");
  }

  async function openConversation(id: string) {
    try {
      const conv = await research.getConversation(id);
      const msgs = conv.messages as Msg[];
      setMessages(msgs);
      idRef.current = msgs.reduce((mx, m) => Math.max(mx, m.id), 0);
      setConvId(conv.id);
      const lastAnswered = [...msgs].reverse().find((m) => m.role === "assistant" && m.answer);
      setActiveId(lastAnswered ? lastAnswered.id : null);
      setView("chat");
    } catch {
      toast.error("Could not open that conversation");
    }
  }

  const activeAnswer = messages.find((m) => m.id === activeId)?.answer ?? null;
  const lastId = messages.length ? messages[messages.length - 1].id : null;

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, pending]);

  async function send(text: string) {
    const q = text.trim();
    if (!q || pending) return;
    const history: ChatHistoryItem[] = messages.map((m) => ({ role: m.role, content: m.content }));
    const userMsg: Msg = { id: ++idRef.current, role: "user", content: q };
    setMessages((m) => [...m, userMsg]);
    setInput("");
    setPending(true);
    try {
      const turn = await research.chat(q, history, deep);
      const aId = ++idRef.current;
      setMessages((m) => [...m, { id: aId, role: "assistant", content: turn.assistant, answer: turn.answer }]);
      setActiveId(aId);
    } catch (e) {
      setMessages((m) => [
        ...m,
        { id: ++idRef.current, role: "assistant", content: `⚠️ Could not reach the research engine — ${e instanceof Error ? e.message : "error"}.` },
      ]);
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="flex h-[78vh] flex-col overflow-hidden rounded-[16px] border border-[var(--color-border)] bg-[var(--color-surface)]">
      {/* ─── segmented control header ─── */}
      <div className="flex items-center gap-2 border-b border-[var(--color-border)] px-4 py-2">
        <Segmented
          aria-label="Research view"
          value={view}
          onChange={setView}
          options={[
            { value: "chat", label: "Chat" },
            { value: "history", label: "History" },
          ]}
        />
        <button
          type="button"
          onClick={() => setDeep((d) => !d)}
          aria-pressed={deep}
          className={`ml-auto rounded-full px-3 py-1 text-[11px] font-mono uppercase tracking-[0.15em] transition ${
            deep
              ? "bg-[var(--color-accent)] text-white"
              : "border border-[var(--color-border)] text-[var(--color-fg-muted)]"
          }`}
          title="Web search runs on every question. Deep dive makes it longer and multi-round."
        >
          Deep dive
        </button>
      </div>

      {/* ─── body ─── */}
      {view === "history" ? (
        <div className="flex-1 overflow-y-auto p-8">
          <History currentId={convId} onOpen={openConversation} onNew={newChat} />
        </div>
      ) : (
        <div className="flex min-h-0 min-w-0 flex-1">
          {/* chat column */}
          <div className="flex min-h-0 min-w-0 flex-1 flex-col">
            <div className="flex-1 overflow-y-auto px-6 py-6">
              {messages.length === 0 ? (
                <div className="mx-auto mt-10 max-w-xl text-center">
                  <Eyebrow>Research Copilot</Eyebrow>
                  <h1 className="mt-3 text-3xl leading-tight text-[var(--color-fg)]" style={SERIF}>
                    Ask anything. Every figure traces back to where it came from.
                  </h1>
                  <div className="mt-6 flex flex-wrap justify-center gap-2">
                    {SUGGESTIONS.map((s) => (
                      <button
                        key={s}
                        onClick={() => send(s)}
                        className="rounded-full border border-[var(--color-border)] bg-[var(--color-bg)] px-3 py-1.5 font-mono text-[11px] text-[var(--color-fg-dim)] transition-colors hover:border-[var(--color-fg-muted)] hover:text-[var(--color-fg)]"
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="mx-auto max-w-2xl space-y-5">
                  {messages.map((m) =>
                    m.role === "user" ? (
                      <div key={m.id} className="flex justify-end animate-[slideInRight_0.3s_ease-out_both]">
                        <div className="max-w-[80%] rounded-[12px] border-l-2 border-[var(--color-accent)] bg-[var(--color-surface-2)] px-4 py-2.5 font-mono text-[13px] text-[var(--color-fg)]">
                          {m.content}
                        </div>
                      </div>
                    ) : (
                      <div key={m.id} className="space-y-2 animate-[fadeSlideIn_0.35s_ease-out_both]">
                        <AssistantNarration text={m.content} reveal={m.id === lastId} />
                        {m.answer && (
                          <div className="flex flex-wrap items-center gap-2 pt-1">
                            <button
                              onClick={() => setActiveId(m.id)}
                              className={`rounded-md border px-3 py-1 font-mono text-[10px] uppercase tracking-wider transition-colors ${
                                activeId === m.id
                                  ? "border-[var(--color-accent)] text-[var(--color-fg)]"
                                  : "border-[var(--color-border)] text-[var(--color-fg-dim)] hover:border-[var(--color-fg-muted)]"
                              }`}
                            >
                              {m.answer.claims.length} cited findings ↗
                            </button>
                            {m.answer.claims.length > 0 && (
                              <button
                                onClick={() => {
                                  saveArtefact({
                                    kind: "research",
                                    title: m.answer!.question || "Research answer",
                                    sourceCount: m.answer!.sources_used.length,
                                    payload: m.answer!,
                                  });
                                  setSavedIds((s) => new Set(s).add(m.id));
                                  toast.success("Saved to Artefacts");
                                }}
                                className="rounded-md border border-[var(--color-border)] px-3 py-1 font-mono text-[10px] uppercase tracking-wider text-[var(--color-fg-dim)] hover:border-[var(--color-accent)] hover:text-[var(--color-fg)]"
                              >
                                ★ Save
                              </button>
                            )}
                            <span className="font-mono text-[10px] uppercase tracking-wider text-[var(--color-fg-muted)]">
                              {m.answer.sources_used.join(" · ") || "no sources"}
                            </span>
                          </div>
                        )}
                        {m.answer && m.answer.claims.length > 0 && !savedIds.has(m.id) && (
                          <p className="pt-1 text-[11px] text-[var(--color-fg-muted)]">
                            This looks worth keeping.{" "}
                            <button
                              className="text-[var(--color-accent)] hover:underline"
                              onClick={() => {
                                saveArtefact({
                                  kind: "research",
                                  title: m.answer!.question || "Research answer",
                                  sourceCount: m.answer!.sources_used.length,
                                  payload: m.answer!,
                                });
                                setSavedIds((s) => new Set(s).add(m.id));
                                toast.success("Saved to Artefacts");
                              }}
                            >
                              Save to Artefacts
                            </button>
                          </p>
                        )}
                      </div>
                    ),
                  )}
                  {pending && <ThinkingSequence />}
                  <div ref={endRef} />
                </div>
              )}
            </div>

            {/* composer */}
            <form
              onSubmit={(e) => { e.preventDefault(); send(input); }}
              className="border-t border-[var(--color-border)] p-4"
            >
              <div className="mx-auto flex max-w-2xl items-center gap-3 rounded-[12px] border border-[var(--color-border)] bg-[var(--color-bg)] px-4 py-3 transition-colors focus-within:border-[var(--color-accent)]">
                <span className="font-mono text-sm text-[var(--color-accent)]">›</span>
                <input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Ask a follow-up — it remembers the conversation…"
                  className="w-full bg-transparent font-mono text-sm text-[var(--color-fg)] placeholder:text-[var(--color-fg-muted)] focus:outline-none"
                  autoFocus
                />
                <Button type="submit" size="sm" disabled={pending || !input.trim()} className="shrink-0">
                  {pending ? "…" : "Ask"}
                </Button>
              </div>
            </form>
          </div>

          {/* artifact panel */}
          <div className="hidden w-[42%] max-w-[560px] shrink-0 overflow-hidden border-l border-[var(--color-border)] bg-[var(--color-bg)] lg:block">
            {activeAnswer ? (
              <Artifact answer={activeAnswer} />
            ) : (
              <div className="flex h-full items-center justify-center p-8 text-center">
                <p className="max-w-xs text-sm text-[var(--color-fg-muted)]">
                  Ask a question — the cited dossier appears here, with every figure linked to its source.
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
