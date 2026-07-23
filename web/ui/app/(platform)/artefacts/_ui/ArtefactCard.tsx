"use client";

import { Diamond, MessagesSquare, Star, Terminal, ClipboardList } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { Artefact } from "@/lib/artefacts";

// Per-kind glyph → lucide icon. Falls back to `Diamond` (the same icon used
// for the Artefacts nav item) for any kind not explicitly mapped.
const KIND_ICON: Record<string, LucideIcon> = {
  research: Terminal,
  debate: MessagesSquare,
  clip: ClipboardList,
};

function kindIcon(kind: string): LucideIcon {
  return KIND_ICON[kind] ?? Diamond;
}

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
  const Icon = kindIcon(artefact.kind);
  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onOpen}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") onOpen();
      }}
      className="elevated lift group relative flex cursor-pointer flex-col overflow-hidden rounded-[10px] border border-[var(--color-border)] p-4 text-left"
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
          <Icon size={11} strokeWidth={2} aria-hidden />
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
            "inline-flex h-6 w-6 items-center justify-center rounded-full transition-all duration-150",
            artefact.starred
              ? "scale-110 text-[var(--color-accent)]"
              : "text-[var(--color-fg-muted)] hover:scale-110 hover:text-[var(--color-fg-dim)]",
          ].join(" ")}
        >
          <Star size={13} strokeWidth={1.75} fill={artefact.starred ? "currentColor" : "none"} />
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
