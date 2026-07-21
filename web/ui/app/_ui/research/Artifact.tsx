"use client";

import { useMemo, useState } from "react";
import type { CitedAnswer, Claim, ResearchRecord } from "@/lib/research";
import { SERIF, formatRecord } from "@/lib/research-format";

function SourceChip({ p }: { p: ResearchRecord["provenance"] }) {
  return (
    <a
      href={p.locator}
      target="_blank"
      rel="noreferrer"
      title={`Verify at source — ${p.locator}`}
      className="group inline-flex items-center gap-1.5 rounded-full border border-[var(--color-border)] bg-[var(--color-surface-2)] px-2.5 py-1 font-mono text-[10px] uppercase tracking-wider text-[var(--color-fg-dim)] transition-colors hover:border-[var(--color-accent)] hover:text-[var(--color-fg)]"
    >
      <span className="h-1.5 w-1.5 rounded-full bg-[var(--color-accent)]" />
      {p.source}
      {p.as_of && <span className="text-[var(--color-fg-muted)]">· {p.as_of}</span>}
      <span className="opacity-40 transition-opacity group-hover:opacity-100">↗</span>
    </a>
  );
}

function ClaimCard({ claim, byId }: { claim: Claim; byId: Map<string, ResearchRecord> }) {
  const records = claim.record_ids.map((id) => byId.get(id)).filter(Boolean) as ResearchRecord[];
  if (records.length === 0) return null;
  const { label, display } = formatRecord(records[0]);
  return (
    <div className="flex flex-col justify-between rounded-[12px] border border-[var(--color-border)] bg-[var(--color-surface)] p-4 transition-colors hover:border-[var(--color-fg-muted)]">
      <div>
        <p className="font-mono text-[9px] uppercase tracking-[0.15em] text-[var(--color-fg-muted)]">
          {label}
        </p>
        <p className="mt-1.5 text-xl text-[var(--color-fg)]" style={SERIF}>
          {display}
        </p>
      </div>
      <div className="mt-3 flex flex-wrap gap-1.5">
        {records.map((r, i) => (
          <SourceChip key={i} p={r.provenance} />
        ))}
        {records.length > 1 && (
          <span className="inline-flex items-center font-mono text-[9px] uppercase tracking-wider text-[var(--color-accent)]">
            corroborated ×{records.length}
          </span>
        )}
      </div>
    </div>
  );
}

function chip(label: string, tone: "used" | "off" | "muted") {
  const cls =
    tone === "used"
      ? "bg-[var(--color-accent-soft)] text-[var(--color-fg)]"
      : tone === "off"
        ? "border border-dashed border-[var(--color-border)] text-[var(--color-fg-muted)] line-through decoration-[var(--color-fg-muted)]/50"
        : "text-[var(--color-fg-muted)]";
  return (
    <span
      key={label}
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 font-mono text-[10px] uppercase tracking-wider ${cls}`}
    >
      {tone === "used" && <span className="h-1.5 w-1.5 rounded-full bg-[var(--color-accent)]" />}
      {label}
    </span>
  );
}

export function Artifact({ answer }: { answer: CitedAnswer }) {
  const [showRaw, setShowRaw] = useState(false);
  const byId = useMemo(() => {
    const m = new Map<string, ResearchRecord>();
    answer.records.forEach((r) => m.set(r.id, r));
    return m;
  }, [answer]);

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-baseline justify-between gap-3 border-b border-[var(--color-border)] px-5 py-4">
        <div className="min-w-0">
          <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--color-accent)]">
            Cited dossier
          </p>
          <p className="mt-1 truncate text-sm text-[var(--color-fg-dim)]" style={SERIF} title={answer.question}>
            {answer.question}
          </p>
        </div>
        <span className="shrink-0 font-mono text-[10px] uppercase tracking-wider text-[var(--color-fg-muted)]">
          {answer.claims.length} findings
        </span>
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto px-5 py-4">
        {/* trust strip */}
        <div className="rounded-[12px] border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
          <div className="grid grid-cols-3 gap-3">
            <div>
              <p className="font-mono text-[9px] uppercase tracking-[0.15em] text-[var(--color-fg-muted)]">Drawn</p>
              <div className="mt-1.5 flex flex-wrap gap-1">
                {answer.sources_used.length ? answer.sources_used.map((s) => chip(s, "used")) : <span className="text-xs text-[var(--color-fg-muted)]">none</span>}
              </div>
            </div>
            <div>
              <p className="font-mono text-[9px] uppercase tracking-[0.15em] text-[var(--color-fg-muted)]">Unavailable</p>
              <div className="mt-1.5 flex flex-wrap gap-1">
                {answer.sources_unavailable.length ? answer.sources_unavailable.map((s) => chip(s, "off")) : <span className="text-xs text-[var(--color-fg-muted)]">—</span>}
              </div>
            </div>
            <div>
              <p className="font-mono text-[9px] uppercase tracking-[0.15em] text-[var(--color-fg-muted)]">Gaps</p>
              <p className="mt-1.5 text-[11px] leading-snug text-[var(--color-fg-muted)]">
                {answer.gaps.length ? `${answer.gaps.length} not covered` : "none"}
              </p>
            </div>
          </div>
        </div>

        {/* finding cards */}
        {answer.claims.length === 0 ? (
          <p className="rounded-[12px] border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-5 text-sm text-[var(--color-fg-muted)]">
            No grounded findings for this query.
          </p>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2">
            {answer.claims.map((c, i) => (
              <ClaimCard key={i} claim={c} byId={byId} />
            ))}
          </div>
        )}

        {/* gaps detail */}
        {answer.gaps.length > 0 && (
          <div className="rounded-[12px] border border-dashed border-[var(--color-border)] p-4">
            <p className="font-mono text-[9px] uppercase tracking-[0.15em] text-[var(--color-fg-muted)]">Coverage gaps</p>
            <ul className="mt-2 space-y-1">
              {answer.gaps.map((g, i) => (
                <li key={i} className="text-[11px] leading-snug text-[var(--color-fg-muted)]">· {g.note}</li>
              ))}
            </ul>
          </div>
        )}

        {/* provenance inspector */}
        <div>
          <button
            onClick={() => setShowRaw((v) => !v)}
            className="font-mono text-[10px] uppercase tracking-wider text-[var(--color-fg-muted)] hover:text-[var(--color-fg-dim)]"
          >
            {showRaw ? "▾ Hide" : "▸ Inspect"} provenance ({answer.records.length} records)
          </button>
          {showRaw && (
            <pre className="mt-2 max-h-64 overflow-auto rounded-[12px] border border-[var(--color-border)] bg-[var(--color-bg)] p-3 font-mono text-[10px] leading-relaxed text-[var(--color-fg-dim)]">
              {JSON.stringify(answer.records, null, 2)}
            </pre>
          )}
        </div>
      </div>

      <p className="border-t border-[var(--color-border)] px-5 py-3 text-[11px] leading-relaxed text-[var(--color-fg-muted)]">
        Every figure links to its source — click any chip to verify. Uncited claims are dropped before they reach you.
      </p>
    </div>
  );
}
