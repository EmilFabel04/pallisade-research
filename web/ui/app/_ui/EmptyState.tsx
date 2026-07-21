"use client";

import type { ReactNode } from "react";

export function EmptyState({
  icon,
  title,
  hint,
  action,
  className = "",
}: {
  icon?: ReactNode;
  title: string;
  hint?: string;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={
        "flex flex-col items-center justify-center gap-2 rounded-lg " +
        "border border-dashed border-[var(--color-border)] p-8 text-center " +
        className
      }
    >
      {icon && (
        <div className="text-[var(--color-fg-muted)] mb-1" aria-hidden>
          {icon}
        </div>
      )}
      <p className="text-sm text-[var(--color-fg-dim)]">{title}</p>
      {hint && (
        <p className="text-[11px] text-[var(--color-fg-muted)]">{hint}</p>
      )}
      {action && <div className="mt-3">{action}</div>}
    </div>
  );
}
