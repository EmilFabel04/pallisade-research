"use client";

import { usePathname } from "next/navigation";
import { NAV_ITEMS } from "./nav";
import { ThemeToggle } from "./ThemeToggle";

export function Topbar({ onOpenPalette }: { onOpenPalette: () => void }) {
  const path = usePathname();
  const current = NAV_ITEMS.find(
    (n) => path === n.href || path.startsWith(n.href + "/"),
  );
  return (
    <header className="flex items-center justify-between border-b border-[var(--color-border)] px-6 py-3">
      <span className="font-mono text-xs uppercase tracking-wider text-[var(--color-fg-dim)]">
        {current?.label ?? "Pallisade"}
      </span>
      <div className="flex items-center gap-2">
        <ThemeToggle />
        <button
          onClick={onOpenPalette}
          className="flex items-center gap-2 rounded-md border border-[var(--color-border)] px-3 py-1.5 text-xs text-[var(--color-fg-muted)] hover:border-[var(--color-fg-muted)]"
        >
          Search…
          <kbd className="font-mono text-[10px]">⌘K</kbd>
        </button>
      </div>
    </header>
  );
}
