"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Plug, FileText, Palette, UserRound } from "lucide-react";
import type { LucideIcon } from "lucide-react";

export interface SettingsSection {
  href: string;
  label: string;
  icon: LucideIcon;
}

export const SETTINGS_SECTIONS: SettingsSection[] = [
  { href: "/settings/connectors", label: "Connectors", icon: Plug },
  { href: "/settings/documents", label: "Documents", icon: FileText },
  { href: "/settings/appearance", label: "Appearance", icon: Palette },
  { href: "/settings/account", label: "Account", icon: UserRound },
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
        const Icon = s.icon;
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
            <Icon size={15} strokeWidth={1.75} aria-hidden="true" />
            {s.label}
          </Link>
        );
      })}
    </nav>
  );
}
