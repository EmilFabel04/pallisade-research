"use client";

import type { ReactNode } from "react";

export function Field({
  label,
  className = "",
  children,
}: {
  label: string;
  className?: string;
  children: ReactNode;
}) {
  return (
    <label className={`block ${className}`}>
      <span className="mb-1.5 block font-mono text-[11px] uppercase tracking-wider text-[var(--color-fg-muted)]">
        {label}
      </span>
      {children}
    </label>
  );
}
