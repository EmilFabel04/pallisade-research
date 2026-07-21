"use client";

import { useEffect, useState } from "react";

const PHASES = [
  "Planning the query",
  "Reading sources",
  "Reconciling figures",
  "Writing the answer",
];

export function ThinkingSequence() {
  const [i, setI] = useState(0);
  useEffect(() => {
    const id = setInterval(() => {
      setI((n) => (n + 1) % PHASES.length);
    }, 1400);
    return () => clearInterval(id);
  }, []);
  return (
    <div className="flex items-center gap-2 font-mono text-[12px] text-[var(--color-fg-muted)]">
      <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[var(--color-accent)]" />
      <span key={i} className="animate-[fadeSlideIn_0.3s_ease-out_both]">
        {PHASES[i]}…
      </span>
    </div>
  );
}
