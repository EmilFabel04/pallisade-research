"use client";

import type { ReactNode } from "react";

export type BadgeTone = "ok" | "warn" | "err" | "info" | "neutral" | "bull" | "bear";

const toneStyles: Record<BadgeTone, string> = {
  ok:
    "text-[var(--tone-ok-fg)] bg-[var(--tone-ok-bg)] border-[var(--tone-ok-bd)]",
  warn:
    "text-[var(--tone-warn-fg)] bg-[var(--tone-warn-bg)] border-[var(--tone-warn-bd)]",
  info:
    "text-[var(--tone-info-fg)] bg-[var(--tone-info-bg)] border-[var(--tone-info-bd)]",
  bull:
    "text-[var(--tone-bull-fg)] bg-[var(--tone-bull-bg)] border-[var(--tone-bull-bd)]",
  bear:
    "text-[var(--tone-bear-fg)] bg-[var(--tone-bear-bg)] border-[var(--tone-bear-bd)]",
  err:
    "text-[var(--color-accent)] bg-[var(--color-accent-soft)] border-[var(--color-accent)]",
  neutral:
    "text-[var(--color-fg-muted)] bg-transparent border-[var(--color-border)]",
};

export function Badge({
  tone = "neutral",
  className = "",
  children,
}: {
  tone?: BadgeTone;
  className?: string;
  children: ReactNode;
}) {
  return (
    <span
      className={
        "inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full border " +
        "font-mono text-[11px] uppercase tracking-wider " +
        toneStyles[tone] +
        " " +
        className
      }
    >
      {children}
    </span>
  );
}
