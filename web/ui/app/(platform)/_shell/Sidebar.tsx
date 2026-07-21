"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { Emblem } from "@/app/_ui";
import { NAV_ITEMS } from "./nav";

export function Sidebar() {
  const path = usePathname();
  const { user, logout } = useAuth();
  return (
    <aside className="flex w-60 shrink-0 flex-col border-r border-[var(--color-border)] bg-[var(--color-bg)]">
      <Link href="/dashboard" className="flex items-center gap-3 px-5 py-5">
        <Emblem size={22} />
        <span className="text-sm font-semibold tracking-tight text-[var(--color-fg)]">
          Pallisade
        </span>
      </Link>
      <nav className="flex-1 space-y-1 px-3">
        {NAV_ITEMS.map((item) => {
          const active = path === item.href || path.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-2.5 rounded-md border-l-2 px-3 py-2 font-mono text-[11px] uppercase tracking-wider transition-colors ${
                active
                  ? "border-[var(--color-accent)] bg-[var(--color-accent-soft)] text-[var(--color-fg)]"
                  : "border-transparent text-[var(--color-fg-dim)] hover:text-[var(--color-fg)]"
              }`}
            >
              <span className="text-[13px] leading-none">{item.glyph}</span>
              {item.label}
            </Link>
          );
        })}
      </nav>
      {user && (
        <div className="border-t border-[var(--color-border)] px-3 py-3">
          <p className="px-3 text-xs text-[var(--color-fg-dim)]">{user.name}</p>
          <button
            onClick={logout}
            className="mt-1 block w-full rounded px-3 py-1 text-left font-mono text-[10px] uppercase tracking-wider text-[var(--color-fg-muted)] hover:text-[var(--color-fg)]"
          >
            Sign out
          </button>
        </div>
      )}
    </aside>
  );
}
