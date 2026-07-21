"use client";

import type { Artefact } from "@/lib/artefacts";

const KIND_GLYPH: Record<Artefact["kind"], string> = {
  research: "›_",
  debate: "⇄",
  clip: "◇",
};

const KIND_HUE: Record<Artefact["kind"], string> = {
  research: "rgba(139,11,16,0.18)",
  debate:   "rgba(147,197,253,0.10)",
  clip:     "rgba(110,231,161,0.10)",
};

const KIND_FG: Record<Artefact["kind"], string> = {
  research: "var(--color-accent)",
  debate:   "#93c5fd",
  clip:     "var(--color-positive)",
};

export function ArtefactCard({
  artefact,
  onOpen,
  onToggleStar,
}: {
  artefact: Artefact;
  onOpen: () => void;
  onToggleStar: () => void;
}) {
  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onOpen}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") onOpen();
      }}
      style={{
        /* subtle top-edge inset glow lifts the card */
        boxShadow:
          "0 1px 0 0 rgba(255,255,255,0.04) inset, 0 12px 32px -16px rgba(0,0,0,0.9)",
      }}
      className="group relative flex flex-col overflow-hidden rounded-[10px] border border-[var(--color-border)] bg-[var(--color-surface-2)] p-4 text-left transition-all duration-200 hover:-translate-y-px hover:border-[var(--color-accent)] hover:shadow-[0_0_0_1px_rgba(139,11,16,0.25),0_16px_40px_-16px_rgba(0,0,0,0.9)]"
    >
      {/* crimson left-edge accent bar — appears on hover */}
      <span
        aria-hidden
        className="pointer-events-none absolute inset-y-0 left-0 w-[2px] translate-x-[-2px] rounded-l bg-[var(--color-accent)] opacity-0 transition-all duration-200 group-hover:translate-x-0 group-hover:opacity-100"
      />

      {/* header row: kind tag + star */}
      <div className="flex items-center justify-between">
        <span
          style={{
            background: KIND_HUE[artefact.kind],
            color: KIND_FG[artefact.kind],
          }}
          className="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 font-mono text-[9px] uppercase tracking-[0.18em]"
        >
          <span style={{ color: KIND_FG[artefact.kind] }} className="text-[11px] leading-none">
            {KIND_GLYPH[artefact.kind]}
          </span>
          {artefact.kind}
        </span>

        <span
          role="button"
          aria-label={artefact.starred ? "Unstar" : "Star"}
          tabIndex={0}
          onClick={(e) => {
            e.stopPropagation();
            onToggleStar();
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.stopPropagation();
              onToggleStar();
            }
          }}
          className={[
            "inline-flex h-6 w-6 items-center justify-center rounded-full text-sm transition-all duration-150",
            artefact.starred
              ? "scale-110 text-[var(--color-accent)]"
              : "text-[var(--color-fg-muted)] hover:scale-110 hover:text-[var(--color-fg-dim)]",
          ].join(" ")}
        >
          {artefact.starred ? "★" : "☆"}
        </span>
      </div>

      {/* title */}
      <p className="mt-3 text-sm leading-snug text-[var(--color-fg)] line-clamp-2 group-hover:text-white">
        {artefact.title}
      </p>

      {/* metadata footer */}
      <p className="mt-auto flex items-center gap-1.5 pt-4 font-mono text-[9px] tracking-wider text-[var(--color-fg-muted)]">
        <span>{new Date(artefact.createdAt).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" })}</span>
        <span className="opacity-40">·</span>
        <span>{artefact.sourceCount} {artefact.sourceCount === 1 ? "source" : "sources"}</span>
      </p>
    </div>
  );
}
