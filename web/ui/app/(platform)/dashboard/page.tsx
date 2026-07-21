"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { KPI, Card, PageHeader, SectionCard } from "@/app/_ui";
import { useArtefacts } from "@/lib/artefacts";
import { FALLBACK_STATS } from "@/lib/seed";
import { listPublicRuns } from "@/lib/runs";
import { timeAgo, absoluteTime } from "@/lib/time";

const TILES = [
  { href: "/research", label: "Ask Research", glyph: "›_", desc: "Cited answers across every source." },
  { href: "/debate", label: "Run a Debate", glyph: "⇄", desc: "Watch the agents deliberate live." },
  { href: "/artefacts", label: "Browse Artefacts", glyph: "◇", desc: "Your saved answers and verdicts." },
];

const KIND_LABEL: Record<string, string> = {
  research: "RSH",
  debate: "DEB",
  clip: "CLIP",
};

export default function DashboardPage() {
  const { user } = useAuth();
  const { items: artefacts } = useArtefacts();
  const [runs, setRuns] = useState<number | null>(null);
  const [clock, setClock] = useState("");

  useEffect(() => {
    listPublicRuns()
      .then((d) => setRuns(d.runs.length))
      .catch(() => setRuns(null));
  }, []);

  /* Live clock — client-only to avoid hydration mismatch */
  useEffect(() => {
    const tick = () =>
      setClock(
        new Date().toLocaleTimeString("en-US", {
          hour12: false,
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        })
      );
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  const stats = [
    { label: "Questions answered", value: FALLBACK_STATS.questions, live: false },
    { label: "Debates run",        value: runs || FALLBACK_STATS.debates,                  live: runs !== null && runs > 0 },
    { label: "Artefacts saved",    value: artefacts.length || FALLBACK_STATS.artefacts,    live: artefacts.length > 0 },
    { label: "Sources connected",  value: FALLBACK_STATS.sources,                          live: false },
  ];

  const pinned = artefacts.filter((a) => a.starred).slice(0, 4);

  return (
    <div>
      {/* ── Header ─────────────────────────────────────────────────────── */}
      <PageHeader
        eyebrow="Console"
        title={`Welcome back, ${user?.name.split(" ")[0] ?? ""}.`}
      >
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-[var(--tone-ok-fg)] pulse-dot" />
            <span className="font-mono text-[10px] uppercase tracking-widest text-[var(--color-fg-muted)]">
              Live
            </span>
          </div>
          {clock && (
            <span className="font-mono text-[11px] tabular-nums text-[var(--color-fg-muted)]">
              {clock}
            </span>
          )}
        </div>
      </PageHeader>

      {/* ── KPI strip ──────────────────────────────────────────────────── */}
      <section className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((s, i) => (
          <div
            key={s.label}
            className="relative"
            style={{ animation: `fadeSlideIn 0.35s ease ${i * 55}ms both` }}
          >
            {/* Crimson hairline marks live data */}
            {s.live && (
              <span
                aria-hidden
                className="pointer-events-none absolute inset-x-0 top-0 z-10 h-px rounded-t-lg bg-[var(--color-accent)] opacity-60"
              />
            )}
            <KPI label={s.label} value={s.value} />
          </div>
        ))}
      </section>

      {/* ── Quick-launch tiles ─────────────────────────────────────────── */}
      <section className="mb-8 grid gap-4 sm:grid-cols-3">
        {TILES.map((t, i) => (
          <Link
            key={t.href}
            href={t.href}
            className="group"
            style={{ animation: `fadeSlideIn 0.35s ease ${220 + i * 55}ms both` }}
          >
            <Card glow className="relative h-full overflow-hidden">
              {/* Large watermark glyph — depth without noise */}
              <span
                aria-hidden
                className="pointer-events-none absolute -right-2 -top-3 select-none font-mono text-7xl font-bold leading-none text-[var(--color-fg)] opacity-[0.04] transition-opacity duration-300 group-hover:opacity-[0.08]"
              >
                {t.glyph}
              </span>

              <div className="relative z-10">
                <div className="font-mono text-xs uppercase tracking-widest text-[var(--color-accent)]">
                  {t.glyph}
                </div>
                <h2 className="mt-3 text-lg text-[var(--color-fg)]">{t.label}</h2>
                <p className="mt-2 text-sm text-[var(--color-fg-muted)]">{t.desc}</p>

                {/* Hover CTA — slides in on hover */}
                <div className="mt-5 flex items-center gap-1 font-mono text-[10px] uppercase tracking-widest text-[var(--color-accent)] opacity-0 transition-opacity duration-200 group-hover:opacity-100">
                  <span>Open</span>
                  <span className="transition-transform duration-200 group-hover:translate-x-0.5">→</span>
                </div>
              </div>
            </Card>
          </Link>
        ))}
      </section>

      {/* ── Info cards ─────────────────────────────────────────────────── */}
      <section className="grid gap-6 lg:grid-cols-2">
        <SectionCard title="Recent activity">
          {artefacts.length === 0 ? (
            <p className="text-sm text-[var(--color-fg-muted)]">No activity yet.</p>
          ) : (
            <ul className="divide-y divide-[var(--color-border)]">
              {artefacts.slice(0, 6).map((a) => (
                <li
                  key={a.id}
                  className="flex items-center gap-3 py-2.5 first:pt-0 last:pb-0"
                >
                  <span className="shrink-0 rounded border border-[var(--color-border)] bg-[var(--color-surface-3)] px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-widest text-[var(--color-fg-muted)]">
                    {KIND_LABEL[a.kind] ?? a.kind}
                  </span>
                  <span className="flex-1 truncate text-sm text-[var(--color-fg-dim)]">
                    {a.title}
                  </span>
                  <span className="shrink-0 font-mono text-[10px] tabular-nums text-[var(--color-fg-muted)]">
                    {timeAgo(a.createdAt)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </SectionCard>

        <SectionCard title="Pinned artefacts">
          {pinned.length === 0 ? (
            <p className="text-sm text-[var(--color-fg-muted)]">Star an artefact to pin it here.</p>
          ) : (
            <ul className="divide-y divide-[var(--color-border)]">
              {pinned.map((a) => (
                <li key={a.id} className="py-2.5 first:pt-0 last:pb-0">
                  <Link href="/artefacts" className="group flex items-center gap-3">
                    <span className="shrink-0 text-xs text-[var(--color-accent)]">★</span>
                    <span className="flex-1 truncate text-sm text-[var(--color-fg-dim)] transition-colors group-hover:text-[var(--color-fg)]">
                      {a.title}
                    </span>
                    <span className="shrink-0 rounded border border-[var(--color-border)] bg-[var(--color-surface-3)] px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-widest text-[var(--color-fg-muted)]">
                      {KIND_LABEL[a.kind] ?? a.kind}
                    </span>
                    <span
                      title={absoluteTime(a.createdAt)}
                      className="shrink-0 font-mono text-[10px] tabular-nums text-[var(--color-fg-muted)]"
                    >
                      {timeAgo(a.createdAt)}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </SectionCard>
      </section>
    </div>
  );
}
