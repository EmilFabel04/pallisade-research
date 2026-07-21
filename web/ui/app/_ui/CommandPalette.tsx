"use client";

import { Command } from "cmdk";
import { useEffect, useMemo } from "react";

export type CommandItem = {
  id: string;
  label: string;
  group?: string;
  shortcut?: string;
  onSelect: () => void;
};

export function CommandPalette({
  open,
  onOpenChange,
  commands,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  commands: CommandItem[];
}) {
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onOpenChange(false);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onOpenChange]);

  const grouped = useMemo(() => {
    const map = new Map<string, CommandItem[]>();
    for (const c of commands) {
      const key = c.group ?? "";
      const arr = map.get(key) ?? [];
      arr.push(c);
      map.set(key, arr);
    }
    return Array.from(map.entries());
  }, [commands]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh]">
      <div
        className="absolute inset-0 bg-black/60"
        onClick={() => onOpenChange(false)}
      />
      <Command
        label="Command palette"
        className="relative w-[min(560px,92vw)] rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] shadow-2xl"
        loop
      >
        <Command.Input
          placeholder="Search commands, deals, runs…"
          autoFocus
          className="w-full bg-transparent px-4 py-3 font-mono text-sm text-[var(--color-fg)] outline-none border-b border-[var(--color-border)] placeholder:text-[var(--color-fg-muted)]"
        />
        <Command.List className="max-h-[50vh] overflow-y-auto py-2">
          <Command.Empty className="px-4 py-6 text-center text-[12px] text-[var(--color-fg-muted)]">
            No commands match.
          </Command.Empty>
          {grouped.map(([group, items]) => (
            <Command.Group
              key={group || "(none)"}
              heading={group || undefined}
              className="px-2"
            >
              {items.map((c) => (
                <Command.Item
                  key={c.id}
                  value={`${c.group ?? ""} ${c.label}`}
                  onSelect={() => {
                    c.onSelect();
                    onOpenChange(false);
                  }}
                  className="flex items-center justify-between rounded-md px-3 py-2 text-sm text-[var(--color-fg-dim)] aria-selected:bg-[var(--color-accent-soft)] aria-selected:text-[var(--color-fg)] cursor-pointer"
                >
                  <span>{c.label}</span>
                  {c.shortcut && (
                    <kbd className="font-mono text-[10px] px-1.5 py-0.5 rounded border border-[var(--color-border)] text-[var(--color-fg-muted)]">
                      {c.shortcut}
                    </kbd>
                  )}
                </Command.Item>
              ))}
            </Command.Group>
          ))}
        </Command.List>
      </Command>
    </div>
  );
}
