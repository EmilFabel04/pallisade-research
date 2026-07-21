"use client";

import { useId, useState, type ReactNode } from "react";
import { timeAgo, absoluteTime } from "@/lib/time";

export interface CollapsibleProps {
  label: ReactNode;
  summary?: string;
  chip?: ReactNode;
  timestamp?: string;
  defaultOpen?: boolean;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  children: ReactNode;
}

export function Collapsible({
  label,
  summary,
  chip,
  timestamp,
  defaultOpen = false,
  open: controlledOpen,
  onOpenChange,
  children,
}: CollapsibleProps) {
  const [uncontrolled, setUncontrolled] = useState(defaultOpen);
  const isControlled = controlledOpen !== undefined;
  const open = isControlled ? controlledOpen : uncontrolled;
  const bodyId = useId();

  function toggle() {
    const next = !open;
    if (!isControlled) setUncontrolled(next);
    onOpenChange?.(next);
  }

  return (
    <div>
      <button
        type="button"
        onClick={toggle}
        aria-expanded={open}
        aria-controls={open ? bodyId : undefined}
        className="flex w-full items-center gap-3 py-1 text-left"
      >
        {label && <span className="shrink-0 text-sm font-medium">{label}</span>}
        {chip}
        {!open && summary && (
          <span className="min-w-0 flex-1 truncate text-sm opacity-70">
            {summary}
          </span>
        )}
        <span className="ml-auto flex shrink-0 items-center gap-3">
          {timestamp && (
            <span
              title={absoluteTime(timestamp)}
              className="font-mono text-[10px] tabular-nums text-[var(--color-fg-muted)]"
            >
              {timeAgo(timestamp)}
            </span>
          )}
          <span
            aria-hidden
            className={
              "font-mono text-sm leading-none opacity-60 transition-transform duration-150 " +
              (open ? "rotate-90" : "")
            }
          >
            ▸
          </span>
        </span>
      </button>
      {open && (
        <div id={bodyId} className="mt-2">
          {children}
        </div>
      )}
    </div>
  );
}
