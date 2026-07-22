"use client";

import type { ReactNode } from "react";

export function Eyebrow({
  muted = false,
  className = "",
  children,
}: {
  muted?: boolean;
  className?: string;
  children: ReactNode;
}) {
  const tone = muted
    ? "text-[10px] tracking-widest text-[var(--color-fg-muted)]"
    : "text-[11px] tracking-[0.2em] text-[var(--color-accent)]";
  return (
    <p className={`font-mono uppercase ${tone} ${className}`}>{children}</p>
  );
}
