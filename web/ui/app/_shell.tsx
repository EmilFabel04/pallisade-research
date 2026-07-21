"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { CommandPalette, Emblem, type CommandItem } from "./_ui";
import { PLATFORM_PREFIXES } from "./(platform)/_shell/nav";

export function Shell({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const path = usePathname();
  const router = useRouter();
  const isPlatform = PLATFORM_PREFIXES.some((p) => path === p || path.startsWith(p + "/"));
  const hideChrome = path === "/login" || path.startsWith("/auth/");

  const [paletteOpen, setPaletteOpen] = useState(false);

  useEffect(() => {
    function isEditable(el: Element | null): boolean {
      if (!el) return false;
      const tag = el.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return true;
      if ((el as HTMLElement).isContentEditable) return true;
      return false;
    }

    function onKey(e: KeyboardEvent) {
      const isMeta = e.metaKey || e.ctrlKey;
      if (isMeta && e.key.toLowerCase() === "k") {
        if (isEditable(document.activeElement)) return;
        e.preventDefault();
        setPaletteOpen((o) => !o);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const commands: CommandItem[] = useMemo(() => {
    const nav: CommandItem[] = [
      { id: "home", group: "Navigate", label: "Home", onSelect: () => router.push("/") },
      { id: "research", group: "Navigate", label: "Research", onSelect: () => router.push("/research") },
      { id: "public-new", group: "Navigate", label: "Public — new dossier", shortcut: "N", onSelect: () => router.push("/public") },
      { id: "public-history", group: "Navigate", label: "Public — history", onSelect: () => router.push("/public/runs") },
    ];
    const account: CommandItem[] = [
      { id: "change-password", group: "Account", label: "Change password", onSelect: () => router.push("/auth/change-password") },
      { id: "sign-out", group: "Account", label: "Sign out", onSelect: () => logout() },
    ];
    return [...nav, ...account];
  }, [router, logout]);

  const sectionLabel = path.startsWith("/public") ? "Public Stock" : "Console";

  if (isPlatform) return <>{children}</>;

  return (
    <div className="mx-auto max-w-7xl px-6 py-8">
      {!hideChrome && (
        <header className="mb-10 flex items-center justify-between border-b border-[var(--color-border)] pb-5 no-print">
          <Link href="/" className="flex items-center gap-3">
            <Emblem size={24} />
            <span className="text-base font-semibold text-[var(--color-fg)]">
              Pallisade
            </span>
            <span className="text-[var(--color-fg-muted)]">/</span>
            <span className="font-mono text-xs uppercase tracking-wider text-[var(--color-fg-dim)]">
              {sectionLabel}
            </span>
          </Link>
          <nav className="flex items-center gap-6 text-xs font-mono uppercase tracking-wider text-[var(--color-fg-dim)]">
            <Link href="/" className="hover:text-[var(--color-fg)]">
              Home
            </Link>
            <Link href="/research" className="hover:text-[var(--color-fg)]">
              Research
            </Link>
            {user && (
              <details className="relative">
                <summary className="cursor-pointer list-none">
                  {user.name}
                </summary>
                <div className="absolute right-0 mt-2 w-48 rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] p-2 text-xs">
                  <Link
                    href="/auth/change-password"
                    className="block rounded px-2 py-1 hover:bg-[var(--color-accent-soft)]"
                  >
                    Change password
                  </Link>
                  <button
                    onClick={logout}
                    className="block w-full rounded px-2 py-1 text-left hover:bg-[var(--color-accent-soft)]"
                  >
                    Sign out
                  </button>
                </div>
              </details>
            )}
          </nav>
        </header>
      )}
      {children}
      {!hideChrome && (
        <footer className="mt-16 border-t border-[var(--color-border)] pt-5 text-[11px] leading-relaxed text-[var(--color-fg-muted)] no-print">
          <p>
            Research output produced by an automated multi-agent system.
            Provided for use by licensed financial services providers and
            qualified professional analysts.{" "}
            <strong className="text-[var(--color-fg-dim)]">
              This is not financial, investment, or trading advice.
            </strong>
          </p>
        </footer>
      )}
      <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} commands={commands} />
    </div>
  );
}
