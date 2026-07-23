"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LogOut } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { Emblem } from "@/app/_ui";
import { NAV_ITEMS } from "./nav";

export function Sidebar() {
  const path = usePathname();
  const { user, logout } = useAuth();
  return (
    <aside className="flex w-60 shrink-0 flex-col border-r border-[var(--color-border)] bg-gradient-to-b from-[var(--color-surface)] to-[var(--color-bg)]">
      <Link href="/dashboard" className="flex items-center gap-3 px-5 py-5">
        <Emblem size={22} />
        <span className="text-sm font-semibold tracking-tight text-[var(--color-fg)]">Pallisade</span>
      </Link>
      <nav className="flex-1 space-y-1 px-3">
        {NAV_ITEMS.map((item) => {
          const active = path === item.href || path.startsWith(item.href + "/");
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={active ? "page" : undefined}
              className={`flex items-center gap-3 rounded-md border-l-2 px-3 py-2 font-mono text-[11px] uppercase tracking-wider transition-all duration-150 ${
                active
                  ? "border-[var(--color-accent)] bg-[var(--color-accent-soft)] text-[var(--color-fg)] shadow-[var(--shadow-accent-soft)]"
                  : "border-transparent text-[var(--color-fg-dim)] hover:text-[var(--color-fg)] hover:bg-[var(--overlay-hairline)]"
              }`}
            >
              <Icon size={16} strokeWidth={1.75} aria-hidden="true" className={active ? "text-[var(--color-accent)]" : ""} />
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
            className="mt-1 flex w-full items-center gap-2 rounded px-3 py-1.5 text-left font-mono text-[10px] uppercase tracking-wider text-[var(--color-fg-muted)] transition-colors hover:text-[var(--color-fg)]"
          >
            <LogOut size={13} strokeWidth={1.75} aria-hidden="true" />
            Sign out
          </button>
        </div>
      )}
    </aside>
  );
}
