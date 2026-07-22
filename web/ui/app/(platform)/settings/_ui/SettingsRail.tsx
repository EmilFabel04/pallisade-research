"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export interface SettingsSection {
  href: string;
  label: string;
  glyph: string;
}

export const SETTINGS_SECTIONS: SettingsSection[] = [
  { href: "/settings/connectors", label: "Connectors", glyph: "⚙" },
  { href: "/settings/documents", label: "Documents", glyph: "◇" },
];

export function SettingsRail() {
  const path = usePathname();
  return (
    <nav
      aria-label="Settings sections"
      className="flex gap-1 overflow-x-auto md:flex-col md:overflow-visible"
    >
      {SETTINGS_SECTIONS.map((s) => {
        const active = path === s.href || path.startsWith(s.href + "/");
        return (
          <Link
            key={s.href}
            href={s.href}
            aria-current={active ? "page" : undefined}
            className={`flex shrink-0 items-center gap-2.5 rounded-md border-l-2 px-3 py-2 font-mono text-[11px] uppercase tracking-wider transition-colors ${
              active
                ? "border-[var(--color-accent)] bg-[var(--color-accent-soft)] text-[var(--color-fg)]"
                : "border-transparent text-[var(--color-fg-dim)] hover:text-[var(--color-fg)]"
            }`}
          >
            <span className="text-[13px] leading-none">{s.glyph}</span>
            {s.label}
          </Link>
        );
      })}
    </nav>
  );
}
