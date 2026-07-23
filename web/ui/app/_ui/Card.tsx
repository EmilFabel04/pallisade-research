"use client";

import type { HTMLAttributes } from "react";

export function Card({
  glow = false,
  className = "",
  children,
  ...rest
}: HTMLAttributes<HTMLDivElement> & { glow?: boolean }) {
  const base =
    "elevated rounded-lg border border-[var(--color-border)] p-6";
  const glowClasses = glow ? " lift" : "";
  return (
    <div {...rest} className={`${base}${glowClasses} ${className}`}>
      {children}
    </div>
  );
}
