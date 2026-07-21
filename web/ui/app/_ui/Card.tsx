"use client";

import type { HTMLAttributes } from "react";

export function Card({
  glow = false,
  className = "",
  children,
  ...rest
}: HTMLAttributes<HTMLDivElement> & { glow?: boolean }) {
  const base =
    "rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-2)] p-6 transition";
  const glowClasses = glow
    ? " bg-gradient-to-b from-[var(--overlay-hairline)] to-transparent " +
      "hover:shadow-[var(--shadow-accent-soft)] hover:border-[var(--color-accent)]"
    : "";
  return (
    <div {...rest} className={`${base}${glowClasses} ${className}`}>
      {children}
    </div>
  );
}
