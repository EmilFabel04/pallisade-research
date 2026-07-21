"use client";

import { useState } from "react";
import { PageHeader, EmptyState } from "@/app/_ui";
import {
  useArtefacts,
  type Artefact,
  type ArtefactKind,
} from "@/lib/artefacts";
import { ArtefactCard } from "./_ui/ArtefactCard";
import { ArtefactDetail } from "./_ui/ArtefactDetail";

const FILTERS: { key: ArtefactKind | "all" | "starred"; label: string }[] = [
  { key: "all",      label: "All" },
  { key: "research", label: "Research" },
  { key: "debate",   label: "Debate" },
  { key: "clip",     label: "Clips" },
  { key: "starred",  label: "Starred" },
];

export default function ArtefactsPage() {
  const { items, toggleStar } = useArtefacts();
  const [filter, setFilter] = useState<(typeof FILTERS)[number]["key"]>("all");
  const [q, setQ] = useState("");
  const [open, setOpen] = useState<Artefact | null>(null);

  const shown = items.filter((a) => {
    if (filter === "starred" && !a.starred) return false;
    if (filter !== "all" && filter !== "starred" && a.kind !== filter) return false;
    if (q && !a.title.toLowerCase().includes(q.toLowerCase())) return false;
    return true;
  });

  return (
    <div>
      <PageHeader eyebrow="Saved" title="Artefacts">
        <div className="relative">
          <span className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 font-mono text-[10px] text-[var(--color-fg-muted)]">
            ⌕
          </span>
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search…"
            className="rounded-md border border-[var(--color-border)] bg-[var(--color-bg)] py-1.5 pl-7 pr-3 font-mono text-xs text-[var(--color-fg)] placeholder:text-[var(--color-fg-muted)] focus:border-[var(--color-accent)] focus:outline-none transition-colors duration-150"
          />
        </div>
      </PageHeader>

      {/* kind / starred filters */}
      <div className="mb-6 flex flex-wrap gap-2">
        {FILTERS.map((f) => (
          <button
            key={f.key}
            onClick={() => setFilter(f.key)}
            className={[
              "rounded-full border px-3 py-1 font-mono text-[9px] uppercase tracking-[0.16em] transition-all duration-150",
              filter === f.key
                ? "border-[var(--color-accent)] bg-[rgba(139,11,16,0.12)] text-[var(--color-fg)]"
                : "border-[var(--color-border)] text-[var(--color-fg-muted)] hover:border-[var(--color-fg-muted)] hover:text-[var(--color-fg-dim)]",
            ].join(" ")}
          >
            {f.label}
          </button>
        ))}

        {/* item count badge */}
        {shown.length > 0 && (
          <span className="ml-auto self-center font-mono text-[9px] text-[var(--color-fg-muted)]">
            {shown.length} {shown.length === 1 ? "item" : "items"}
          </span>
        )}
      </div>

      {shown.length === 0 ? (
        <EmptyState
          title="No artefacts yet"
          hint="Save a research answer or debate verdict to see it here."
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {shown.map((a, i) => (
            <div
              key={a.id}
              style={{
                /* stagger entrance — pure CSS, no JS dependency */
                animationDelay: `${i * 40}ms`,
                animationFillMode: "both",
              }}
              className="animate-[fadeSlideIn_0.22s_ease-out_both]"
            >
              <ArtefactCard
                artefact={a}
                onOpen={() => setOpen(a)}
                onToggleStar={() => toggleStar(a.id)}
              />
            </div>
          ))}
        </div>
      )}

      {/* detail drawer */}
      {open && (
        <div
          className="fixed inset-0 z-40 flex justify-end"
          onClick={() => setOpen(null)}
        >
          {/* backdrop */}
          <div className="absolute inset-0 bg-black/65 backdrop-blur-[2px]" />

          {/* panel */}
          <div
            className="relative h-full w-[min(640px,92vw)] overflow-y-auto border-l border-[var(--color-border)] bg-[var(--color-surface)] shadow-[var(--shadow-card-lg)] animate-[slideInRight_0.22s_cubic-bezier(0.22,1,0.36,1)_both]"
            onClick={(e) => e.stopPropagation()}
          >
            {/* close row */}
            <div className="sticky top-0 z-10 flex items-center justify-between border-b border-[var(--color-border)] bg-[var(--color-surface)] px-5 py-3">
              <span className="font-mono text-[9px] uppercase tracking-[0.2em] text-[var(--color-fg-muted)]">
                {open.title}
              </span>
              <button
                onClick={() => setOpen(null)}
                aria-label="Close"
                className="rounded-full p-1.5 text-[var(--color-fg-muted)] transition-colors hover:bg-[var(--color-border)] hover:text-[var(--color-fg)]"
              >
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                  <path d="M1 1l10 10M11 1L1 11" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                </svg>
              </button>
            </div>

            <ArtefactDetail artefact={open} />
          </div>
        </div>
      )}
    </div>
  );
}
