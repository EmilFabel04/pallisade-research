"use client";

import type { Artefact } from "@/lib/artefacts";
import type { CitedAnswer } from "@/lib/research";
import { Artifact } from "@/app/_ui/research/Artifact";
import type { DebateTranscript, DebateTurn } from "@/lib/seed";
import { timeAgo, absoluteTime } from "@/lib/time";
import { CollapsibleMarkdown } from "@/app/(platform)/debate/_ui/CollapsibleMarkdown";
import { Badge } from "@/app/_ui";

/* ────────────────────────────────────────────────────────
   Role colour palette — agent → visual accent
   ──────────────────────────────────────────────────────── */
const ROLE_STYLES: Record<
  string,
  { fg: string; bg: string; border: string }
> = {
  analyst: { fg: "#2563eb", bg: "rgba(37,99,235,0.07)", border: "rgba(37,99,235,0.22)" },
  bull:    { fg: "var(--color-positive)", bg: "rgba(21,128,61,0.07)", border: "rgba(21,128,61,0.22)" },
  bear:    { fg: "var(--color-negative)", bg: "rgba(185,28,28,0.07)", border: "rgba(185,28,28,0.22)" },
  risk:    { fg: "#b45309", bg: "rgba(180,83,9,0.07)", border: "rgba(180,83,9,0.22)" },
};

function roleStyle(role: string) {
  return ROLE_STYLES[role] ?? {
    fg: "var(--color-fg-dim)",
    bg: "var(--overlay-hairline)",
    border: "var(--color-border)",
  };
}

/* ────────────────────────────────────────────────────────
   Debate transcript view
   ──────────────────────────────────────────────────────── */
function DebateView({ d }: { d: DebateTranscript }) {
  const confidence = Math.round(d.verdict.confidence * 100);
  const verdictColor =
    d.verdict.recommendation === "approve"
      ? "var(--color-positive)"
      : d.verdict.recommendation === "reject"
      ? "var(--color-negative)"
      : "var(--color-fg-dim)";

  return (
    <div className="flex h-full flex-col">
      {/* verdict header */}
      <div className="border-b border-[var(--color-border)] px-5 py-4">
        <p className="font-mono text-[9px] uppercase tracking-[0.22em] text-[var(--color-fg-muted)]">
          Debate verdict
        </p>
        <div className="mt-2 flex items-baseline gap-3">
          <span
            style={{ color: verdictColor }}
            className="font-mono text-xs uppercase tracking-widest"
          >
            {d.verdict.recommendation}
          </span>
          <span className="font-mono text-[10px] text-[var(--color-fg-muted)]">
            {confidence}% confidence
          </span>
        </div>
        <p className="mt-2 text-[13px] leading-relaxed text-[var(--color-fg-dim)]">
          {d.verdict.thesis}
        </p>
        {/* confidence bar */}
        <div className="mt-3 h-[2px] w-full overflow-hidden rounded-full bg-[var(--color-border)]">
          <div
            style={{ width: `${confidence}%`, background: verdictColor }}
            className="h-full rounded-full transition-all duration-500"
          />
        </div>
      </div>

      {/* turn thread */}
      <div className="flex-1 space-y-2 overflow-y-auto px-5 py-4">
        <p className="mb-3 font-mono text-[9px] uppercase tracking-[0.2em] text-[var(--color-fg-muted)]">
          {d.turns.length} turns · {d.subject}
        </p>
        {d.turns.map((t: DebateTurn, i: number) => {
          const rs = roleStyle(t.role);
          return (
            <div
              key={i}
              style={{
                background: rs.bg,
                borderColor: rs.border,
              }}
              className="rounded-[8px] border p-3 transition-colors"
            >
              <CollapsibleMarkdown
                body={t.text}
                label={<span className="font-medium">{t.agent}</span>}
                chip={
                  <Badge tone={t.role === "bull" ? "bull" : t.role === "bear" ? "bear" : "neutral"}>
                    {t.role}
                  </Badge>
                }
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ────────────────────────────────────────────────────────
   Clip (markdown table) view
   ──────────────────────────────────────────────────────── */
function ClipView({ payload }: { payload: string }) {
  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-[var(--color-border)] px-5 py-4">
        <p className="font-mono text-[9px] uppercase tracking-[0.22em] text-[var(--color-fg-muted)]">
          Clipped table
        </p>
      </div>
      <div className="flex-1 overflow-auto px-5 py-4">
        <div className="prose-research">
          <ClipTable raw={payload} />
        </div>
      </div>
    </div>
  );
}

/* Naively parse a GFM table string into an HTML table */
function ClipTable({ raw }: { raw: string }) {
  const lines = raw
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean);

  if (lines.length < 2) {
    return (
      <pre className="overflow-x-auto font-mono text-xs text-[var(--color-fg-dim)]">
        {raw}
      </pre>
    );
  }

  const parseRow = (line: string) =>
    line
      .replace(/^\|/, "")
      .replace(/\|$/, "")
      .split("|")
      .map((c) => c.trim());

  const headers = parseRow(lines[0]);
  // lines[1] is separator row
  const rows = lines.slice(2).map(parseRow);

  return (
    <table>
      <thead>
        <tr>
          {headers.map((h, i) => (
            <th key={i}>{h}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row, ri) => (
          <tr key={ri}>
            {row.map((cell, ci) => (
              <td key={ci}>{cell}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/* ────────────────────────────────────────────────────────
   Main export
   ──────────────────────────────────────────────────────── */
function renderBody(artefact: Artefact) {
  if (artefact.kind === "research") {
    return <Artifact answer={artefact.payload as CitedAnswer} />;
  }
  if (artefact.kind === "debate") {
    return <DebateView d={artefact.payload as DebateTranscript} />;
  }
  // clip
  return <ClipView payload={String(artefact.payload)} />;
}

export function ArtefactDetail({ artefact }: { artefact: Artefact }) {
  return (
    <div className="flex h-full flex-col">
      <div className="mb-3 flex shrink-0 items-center justify-between">
        <span className="truncate text-sm font-medium">{artefact.title}</span>
        <span
          title={absoluteTime(artefact.createdAt)}
          className="shrink-0 font-mono text-[10px] tabular-nums text-[var(--color-fg-muted)]"
        >
          {timeAgo(artefact.createdAt)}
        </span>
      </div>
      <div className="flex-1 min-h-0">{renderBody(artefact)}</div>
    </div>
  );
}
