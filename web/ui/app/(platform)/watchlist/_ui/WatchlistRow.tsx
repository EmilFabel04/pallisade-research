"use client";

import { useEffect, useRef, useState } from "react";
import { Sparkline, Badge } from "@/app/_ui";
import { useArtefacts } from "@/lib/artefacts";
import type { WatchlistItem, Conviction } from "@/lib/watchlist";
import { timeAgo, absoluteTime } from "@/lib/time";

const CONVICTIONS: Conviction[] = ["bull", "bear", "watch"];
const CONVICTION_TONE: Record<Conviction, "ok" | "err" | "neutral"> = {
  bull: "ok",
  bear: "err",
  watch: "neutral",
};

export function WatchlistRow({
  item,
  onResearch,
  onDebate,
  onRemove,
  onUpdate,
}: {
  item: WatchlistItem;
  onResearch: () => void;
  onDebate: () => void;
  onRemove: () => void;
  onUpdate: (patch: { conviction?: Conviction; note?: string }) => void;
}) {
  const { items: artefacts } = useArtefacts();
  const [editingNote, setEditingNote] = useState(false);
  const [noteDraft, setNoteDraft] = useState(item.note);
  const cancelling = useRef(false);

  useEffect(() => {
    if (!editingNote) setNoteDraft(item.note);
  }, [item.note, editingNote]);

  const coverage = artefacts.find((a) =>
    a.title.toUpperCase().startsWith(item.ticker.toUpperCase()),
  );

  const tone =
    item.changePct > 0 ? "ok" : item.changePct < 0 ? "err" : "neutral";
  const changeColor =
    item.changePct > 0
      ? "text-[var(--color-positive)]"
      : item.changePct < 0
      ? "text-[var(--color-negative)]"
      : "text-[var(--color-fg-muted)]";

  function cycleConviction() {
    const idx = CONVICTIONS.indexOf(item.conviction);
    onUpdate({ conviction: CONVICTIONS[(idx + 1) % CONVICTIONS.length] });
  }

  function commitNote() {
    if (cancelling.current) {
      cancelling.current = false;
      setEditingNote(false);
      return;
    }
    setEditingNote(false);
    if (noteDraft !== item.note) onUpdate({ note: noteDraft });
  }

  return (
    <tr className="border-b border-[var(--color-border)] last:border-0 hover:bg-[var(--overlay-hairline)]">
      <td className="px-4 py-3">
        <div className="font-mono text-[var(--color-fg)]">{item.ticker}</div>
        <div className="text-[11px] text-[var(--color-fg-muted)]">{item.name}</div>
      </td>
      <td className="px-4 py-3 text-right font-mono tabular-nums text-[var(--color-fg)]">
        {item.price ? item.price.toFixed(2) : "—"}
      </td>
      <td className={`px-4 py-3 text-right font-mono tabular-nums ${changeColor}`}>
        {item.price ? (
          <>
            {item.changePct > 0 ? "+" : ""}
            {item.changePct.toFixed(2)}%
          </>
        ) : (
          "—"
        )}
      </td>
      <td className="px-4 py-3 text-right font-mono tabular-nums text-[var(--color-fg-dim)]">
        {item.marketCap}
      </td>
      <td className="px-4 py-3 text-right font-mono tabular-nums text-[var(--color-fg-dim)]">
        {item.pe ? item.pe.toFixed(1) : "—"}
      </td>
      <td className="px-4 py-3">
        <Sparkline data={item.spark} tone={tone} />
      </td>
      <td className="px-4 py-3">
        <button onClick={cycleConviction} aria-label={`Conviction: ${item.conviction}. Click to cycle.`} title="Click to change">
          <Badge tone={CONVICTION_TONE[item.conviction]}>{item.conviction}</Badge>
        </button>
      </td>
      <td className="px-4 py-3">
        {coverage ? (
          <Badge tone="info">{coverage.kind}</Badge>
        ) : (
          <span className="font-mono text-[10px] uppercase tracking-wider text-[var(--color-fg-muted)]">
            No coverage
          </span>
        )}
      </td>
      <td className="px-4 py-3 align-top">
        {editingNote ? (
          <input
            value={noteDraft}
            onChange={(e) => setNoteDraft(e.target.value)}
            onBlur={commitNote}
            onKeyDown={(e) => {
              if (e.key === "Enter") commitNote();
              if (e.key === "Escape") {
                cancelling.current = true;
                setNoteDraft(item.note);
                setEditingNote(false);
              }
            }}
            autoFocus
            className="w-40 rounded border border-[var(--color-accent)] bg-[var(--color-bg)] px-2 py-1 text-[12px] text-[var(--color-fg)] focus:outline-none"
          />
        ) : (
          <button
            onClick={() => {
              cancelling.current = false;
              setEditingNote(true);
            }}
            className="max-w-[10rem] truncate text-left text-[12px] text-[var(--color-fg-dim)] hover:text-[var(--color-fg)]"
            title={item.note || "Add note"}
          >
            {item.note || <span className="text-[var(--color-fg-muted)]">Add note…</span>}
          </button>
        )}
      </td>
      <td className="px-4 py-3 text-right">
        <span
          title={absoluteTime(item.addedAt)}
          className="font-mono text-[10px] tabular-nums text-[var(--color-fg-muted)]"
        >
          {timeAgo(item.addedAt)}
        </span>
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center justify-end gap-2">
          <button
            onClick={onResearch}
            className="rounded-md border border-[var(--color-border)] px-2 py-1 font-mono text-[10px] uppercase tracking-wider text-[var(--color-fg-dim)] transition-colors hover:border-[var(--color-accent)] hover:text-[var(--color-fg)]"
          >
            Research
          </button>
          <button
            onClick={onDebate}
            className="rounded-md border border-[var(--color-border)] px-2 py-1 font-mono text-[10px] uppercase tracking-wider text-[var(--color-fg-dim)] transition-colors hover:border-[var(--color-accent)] hover:text-[var(--color-fg)]"
          >
            Debate
          </button>
          <button
            onClick={onRemove}
            aria-label={`Remove ${item.ticker}`}
            className="rounded-md border border-transparent px-2 py-1 font-mono text-[12px] text-[var(--color-fg-muted)] transition-colors hover:text-[var(--color-negative)]"
          >
            ×
          </button>
        </div>
      </td>
    </tr>
  );
}
