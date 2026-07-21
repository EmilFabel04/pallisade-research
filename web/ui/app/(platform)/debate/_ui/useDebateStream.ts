"use client";

import { useEffect, useState } from "react";
import { getDebateRun, STREAM_URL, type DebateStatus, type DebateTurn } from "@/lib/debate";

export interface DebateRunState {
  phase: "idle" | "queued" | "running" | "done" | "error";
  reports: Record<string, string>;
  reportTs: Record<string, string>;
  turns: DebateTurn[];
  statusLine: string | null;
  error: string | null;
  ticker: string | null;
}

interface StreamEvent {
  type: string;
  seq?: number;
  state?: string;
  message?: string;
  key?: string;
  content?: string;
  error?: string;
  phase?: string;
  speaker?: string;
  round?: number;
  text?: string;
  ts?: string;
}

function toPhase(s: DebateStatus | undefined): DebateRunState["phase"] {
  if (s === "failed" || s === "error") return "error";
  if (s === "done") return "done";
  if (s === "running") return "running";
  if (s === "queued") return "queued";
  return "idle";
}

const IDLE: DebateRunState = {
  phase: "idle", reports: {}, reportTs: {}, turns: [], statusLine: null, error: null, ticker: null,
};

export function useDebateStream(runId: string | null): DebateRunState {
  const [state, setState] = useState<DebateRunState>(IDLE);

  // Hydrate persisted state whenever the runId changes.
  useEffect(() => {
    if (!runId) {
      setState(IDLE);
      return;
    }
    setState({ ...IDLE, phase: "queued" });
    let cancelled = false;
    getDebateRun(runId)
      .then((d) => {
        if (cancelled) return;
        setState((prev) => ({
          ...prev,
          reports: d.reports || {},
          ticker: d.ticker,
          error: d.error,
          phase: toPhase(d.status),
        }));
      })
      .catch(() => {
        /* stream will still attach; ignore hydrate failure */
      });
    return () => {
      cancelled = true;
    };
  }, [runId]);

  // Attach the SSE stream.
  useEffect(() => {
    if (!runId) return;
    const es = new EventSource(STREAM_URL(runId), { withCredentials: true });

    es.addEventListener("status", (e: MessageEvent) => {
      const d = JSON.parse(e.data) as StreamEvent;
      setState((prev) => ({
        ...prev,
        statusLine: d.message ?? prev.statusLine,
        phase:
          d.state === "running" && prev.phase !== "done" && prev.phase !== "error"
            ? "running"
            : prev.phase,
      }));
    });
    es.addEventListener("report", (e: MessageEvent) => {
      const d = JSON.parse(e.data) as StreamEvent;
      if (d.key && typeof d.content === "string") {
        setState((prev) => ({
          ...prev,
          reports: { ...prev.reports, [d.key!]: d.content! },
          reportTs: d.ts ? { ...prev.reportTs, [d.key!]: d.ts } : prev.reportTs,
        }));
      }
    });
    // Turns arrive ONLY from the stream (which replays from cursor 0); the
    // hydrate GET must never also supply them or the argument double-renders.
    es.addEventListener("turn", (e: MessageEvent) => {
      const d = JSON.parse(e.data) as StreamEvent;
      if (d.phase !== "invest") return; // risk turns are stored, not rendered
      if (typeof d.seq !== "number" || typeof d.text !== "string") return;
      setState((prev) => {
        if (prev.turns.some((t) => t.seq === d.seq)) return prev; // reconnect guard
        const turn = {
          seq: d.seq!,
          phase: "invest",
          speaker: d.speaker,
          round: d.round ?? 1,
          text: d.text!,
          ts: d.ts,
        } as DebateTurn;
        return { ...prev, turns: [...prev.turns, turn].sort((a, b) => a.seq - b.seq) };
      });
    });
    es.addEventListener("done", () => {
      setState((prev) => ({ ...prev, phase: prev.phase === "error" ? "error" : "done" }));
    });
    es.addEventListener("error", (e: MessageEvent) => {
      try {
        const d = JSON.parse((e as MessageEvent).data) as StreamEvent;
        setState((prev) => ({
          ...prev,
          phase: prev.phase === "done" ? "done" : "error",
          error: d.error ?? "Unknown error",
        }));
      } catch {
        /* transport-level error; handled by close/onerror */
      }
    });
    es.addEventListener("close", () => es.close());
    // Let EventSource auto-reconnect on transient failures: every frame carries
    // `id: <seq>`, so the browser resends Last-Event-ID and the server resumes
    // from that cursor — no gap, no duplicate. Only close when the browser has
    // permanently given up (readyState CLOSED), e.g. a 404/403 on the stream.
    es.onerror = () => {
      if (es.readyState === EventSource.CLOSED) es.close();
    };

    return () => es.close();
  }, [runId]);

  return state;
}
