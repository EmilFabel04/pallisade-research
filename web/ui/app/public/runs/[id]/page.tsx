"use client";

import { use, useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { api } from "@/lib/api";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

type Status = "queued" | "running" | "done" | "error";

const REPORT_META: Record<
  string,
  { label: string; short: string; tone: "analyst" | "research" | "internal" }
> = {
  market_report: { label: "Market Analyst", short: "Market", tone: "analyst" },
  sentiment_report: { label: "Sentiment Analyst", short: "Sentiment", tone: "analyst" },
  news_report: { label: "News Analyst", short: "News", tone: "analyst" },
  fundamentals_report: { label: "Fundamentals Analyst", short: "Fundamentals", tone: "analyst" },
  investment_plan: { label: "Research Manager — Synthesis", short: "Synthesis", tone: "research" },
  trader_investment_plan: { label: "Red Team — Pre-Mortem", short: "Red Team", tone: "research" },
  final_trade_decision: { label: "Portfolio Manager — Internal Verdict", short: "Internal", tone: "internal" },
};

const ORDER = [
  "market_report",
  "sentiment_report",
  "news_report",
  "fundamentals_report",
  "investment_plan",
  "trader_investment_plan",
  "final_trade_decision",
];

interface RunDetail {
  id: string;
  ticker: string;
  trade_date: string;
  asset_type: string;
  analysts: string[];
  status: Status;
  created_at: string;
  reports: Record<string, string>;
  final_state: Record<string, string> | null;
  error: string | null;
}

interface StatusEvent {
  ts: string;
  type: string;
  state?: string;
  message?: string;
  key?: string;
  content?: string;
  error?: string;
}

export default function RunPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);

  const [run, setRun] = useState<RunDetail | null>(null);
  const [statusFeed, setStatusFeed] = useState<StatusEvent[]>([]);
  const [reports, setReports] = useState<Record<string, string>>({});
  const [status, setStatus] = useState<Status>("queued");
  const [error, setError] = useState<string | null>(null);
  const [active, setActive] = useState<string | null>(null);
  const [showInternal, setShowInternal] = useState(false);
  const statusEndRef = useRef<HTMLDivElement | null>(null);

  // initial fetch of run metadata
  useEffect(() => {
    api<RunDetail>(`/api/runs/${id}`)
      .then((data) => {
        setRun(data);
        setReports(data.reports || {});
        setStatus(data.status);
        if (data.error) setError(data.error);
      })
      .catch((e) => setError(String(e)));
  }, [id]);

  // SSE stream
  useEffect(() => {
    const es = new EventSource(`${API_BASE}/api/runs/${id}/stream`, { withCredentials: true });

    es.addEventListener("status", (e: MessageEvent) => {
      const data = JSON.parse(e.data) as StatusEvent;
      setStatusFeed((curr) => [...curr, data]);
      if (data.state === "running") setStatus("running");
    });
    es.addEventListener("report", (e: MessageEvent) => {
      const data = JSON.parse(e.data) as StatusEvent;
      if (data.key && typeof data.content === "string") {
        setReports((curr) => ({ ...curr, [data.key!]: data.content! }));
        setActive((curr) => curr ?? data.key!);
      }
    });
    es.addEventListener("error", (e: MessageEvent) => {
      try {
        const data = JSON.parse((e as MessageEvent).data) as StatusEvent;
        setError(data.error || "Unknown error");
      } catch {
        // SSE connection error — ignored, handled by close
      }
      setStatus("error");
    });
    es.addEventListener("done", () => {
      setStatus("done");
    });
    es.addEventListener("close", () => {
      es.close();
    });
    es.onerror = () => {
      // transport-level error; the server may have closed cleanly
      es.close();
    };

    return () => es.close();
  }, [id]);

  // auto-pick first report as active
  useEffect(() => {
    if (!active) {
      const firstWithData = ORDER.find(
        (k) =>
          k in reports &&
          REPORT_META[k].tone !== "internal" // never auto-open the internal verdict
      );
      if (firstWithData) setActive(firstWithData);
    }
  }, [reports, active]);

  // scroll status feed
  useEffect(() => {
    statusEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [statusFeed.length]);

  const visibleReports = useMemo(
    () =>
      ORDER.filter((k) => k in reports).filter(
        (k) => REPORT_META[k].tone !== "internal" || showInternal
      ),
    [reports, showInternal]
  );

  return (
    <main>
      <div className="no-print">
        <RunHeader run={run} status={status} />

        {error && (
          <div className="mb-6 rounded-md border border-[var(--color-negative)]/40 bg-[var(--color-negative)]/5 p-4 font-mono text-sm text-[var(--color-negative)]">
            <div className="mb-1 text-xs uppercase tracking-wider opacity-80">Run failed</div>
            {error}
          </div>
        )}
      </div>

      <div className="grid grid-cols-12 gap-6 no-print">
        {/* Left: pipeline + status feed */}
        <aside className="col-span-12 lg:col-span-4 space-y-4">
          <PipelinePanel reports={reports} active={active} onPick={setActive} showInternal={showInternal} />
          <StatusFeed events={statusFeed} status={status} endRef={statusEndRef} />
        </aside>

        {/* Right: dossier */}
        <section className="col-span-12 lg:col-span-8">
          <DossierPanel
            run={run}
            reports={reports}
            active={active}
            visibleReports={visibleReports}
            showInternal={showInternal}
            setShowInternal={setShowInternal}
            status={status}
          />
        </section>
      </div>

      {/* Print-only: full dossier — all visible reports concatenated for PDF export. */}
      <PrintableDossier run={run} reports={reports} visibleReports={visibleReports} />
    </main>
  );
}


function PrintableDossier({
  run, reports, visibleReports,
}: {
  run: RunDetail | null;
  reports: Record<string, string>;
  visibleReports: string[];
}) {
  const generated = new Date();
  const sections = visibleReports
    .map((k) => ({ key: k, meta: REPORT_META[k], content: reports[k] }))
    .filter((s) => Boolean(s.content));
  const ticker = run?.ticker ?? "—";
  const shortId = run?.id ? run.id.slice(0, 8) : "—";

  return (
    <div className="print-only print-dossier">
      {/* ---------------- Cover page ---------------- */}
      <section className="print-page print-cover">
        <header className="print-cover-top">
          <div className="print-wordmark">
            <span className="print-emblem-mark">▲</span>
            <span>PALLISADE DATA</span>
          </div>
          <div className="print-cover-eyebrow">Research dossier · v1</div>
        </header>

        <div className="print-cover-body">
          <div className="print-cover-label">Subject</div>
          <h1 className="print-cover-ticker">{ticker}</h1>
          {run?.trade_date && (
            <div className="print-cover-date">As of {run.trade_date}</div>
          )}

          <dl className="print-cover-meta">
            {run?.asset_type && (
              <>
                <dt>Asset class</dt>
                <dd>{run.asset_type}</dd>
              </>
            )}
            {run && run.analysts.length > 0 && (
              <>
                <dt>Analyst coverage</dt>
                <dd>{run.analysts.join(" · ")}</dd>
              </>
            )}
            <dt>Sections</dt>
            <dd>{sections.length} report{sections.length === 1 ? "" : "s"}</dd>
            <dt>Run identifier</dt>
            <dd className="print-mono">{shortId}</dd>
            <dt>Generated</dt>
            <dd>{generated.toLocaleString()}</dd>
          </dl>
        </div>

        <footer className="print-cover-foot">
          <p>
            <strong>Disclaimer.</strong> This dossier is research output produced
            by an automated multi-agent system. It is provided to licensed
            financial services providers and qualified professional analysts for
            informational purposes only. It is not financial, investment, or
            trading advice, and is not an offer or solicitation to buy or sell
            any security. Past performance is not indicative of future results.
            Recipients must form their own conclusions and conduct independent
            due diligence.
          </p>
          <div className="print-cover-foot-row">
            <span>Pallisade Data · pallisadedata.com</span>
            <span className="print-mono">{shortId}</span>
          </div>
        </footer>
      </section>

      {/* ---------------- Table of contents ---------------- */}
      {sections.length > 1 && (
        <section className="print-page print-toc">
          <div className="print-section-band">
            <span>{ticker} · {run?.trade_date}</span>
            <span>Contents</span>
          </div>
          <h2 className="print-toc-title">Contents</h2>
          <ol className="print-toc-list">
            {sections.map((s, i) => (
              <li key={s.key}>
                <span className="print-toc-num">{String(i + 1).padStart(2, "0")}</span>
                <span className="print-toc-label">
                  {s.meta.label}
                  <span className="print-toc-tone"> · {s.meta.tone}</span>
                </span>
                <span className="print-toc-leader" aria-hidden />
              </li>
            ))}
          </ol>
        </section>
      )}

      {/* ---------------- Report sections ---------------- */}
      {sections.length === 0 && (
        <p className="print-empty">No reports available to export yet.</p>
      )}
      {sections.map((s, i) => (
        <section key={s.key} className="print-page print-section">
          <div className="print-section-band">
            <span>{ticker} · {run?.trade_date}</span>
            <span>{s.meta.short}</span>
          </div>
          <header className="print-section-head">
            <span className="print-section-num">{String(i + 1).padStart(2, "0")}</span>
            <div>
              <div className="print-section-eyebrow">{s.meta.tone}</div>
              <h2 className="print-section-title">{s.meta.label}</h2>
            </div>
          </header>

          {s.meta.tone === "internal" && (
            <div className="print-internal-note">
              <strong>Internal model output.</strong> Surfaced for research review
              only. Not a recommendation; users must form their own conclusion.
            </div>
          )}

          <article className="prose-research print-prose">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{s.content}</ReactMarkdown>
          </article>
        </section>
      ))}

      {/* ---------------- Colophon ---------------- */}
      <section className="print-page print-colophon">
        <div className="print-section-band">
          <span>{ticker} · {run?.trade_date}</span>
          <span>Colophon</span>
        </div>
        <h2 className="print-section-title">End of report</h2>
        <p className="print-colophon-body">
          This dossier was produced by Pallisade Data&apos;s automated multi-agent
          research system. Each report represents the independent output of a
          specialised analyst agent or synthesis layer; reports are not
          reconciled against each other and may contain conflicting conclusions
          by design.
        </p>
        <dl className="print-cover-meta">
          <dt>Subject</dt><dd>{ticker} · {run?.trade_date}</dd>
          <dt>Run identifier</dt><dd className="print-mono">{run?.id ?? "—"}</dd>
          <dt>Generated</dt><dd>{generated.toLocaleString()}</dd>
          <dt>Sections included</dt><dd>{sections.map((s) => s.meta.short).join(", ") || "—"}</dd>
        </dl>
        <p className="print-colophon-fineprint">
          © {generated.getFullYear()} Pallisade Data. Not financial advice. For
          authorised recipients only.
        </p>
      </section>
    </div>
  );
}

function RunHeader({ run, status }: { run: RunDetail | null; status: Status }) {
  return (
    <header className="mb-8 flex flex-wrap items-end justify-between gap-4 border-b border-[var(--color-border)] pb-5">
      <div>
        <div className="font-mono text-xs uppercase tracking-widest text-[var(--color-fg-muted)]">
          Dossier
        </div>
        <h1 className="mt-1 font-mono text-4xl tracking-tight">
          {run?.ticker ?? "…"}
          <span className="ml-3 text-base text-[var(--color-fg-muted)]">{run?.trade_date}</span>
        </h1>
        <div className="mt-2 flex items-center gap-2 text-xs text-[var(--color-fg-muted)] font-mono">
          {run && (
            <>
              <span>{run.asset_type}</span>
              <span>·</span>
              <span>{run.analysts.join(" · ")}</span>
              <span>·</span>
              <span className="opacity-60">id {run.id}</span>
            </>
          )}
        </div>
      </div>
      <StatusBadge status={status} />
    </header>
  );
}

function StatusBadge({ status }: { status: Status }) {
  const cfg = {
    queued: { label: "Queued", dot: "bg-[var(--color-fg-muted)]", pulse: false },
    running: { label: "Running", dot: "bg-[var(--color-accent)]", pulse: true },
    done: { label: "Complete", dot: "bg-[var(--color-positive)]", pulse: false },
    error: { label: "Error", dot: "bg-[var(--color-negative)]", pulse: false },
  }[status];
  return (
    <div className="flex items-center gap-2 rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1.5">
      <span className={`h-2 w-2 rounded-full ${cfg.dot} ${cfg.pulse ? "pulse-dot" : ""}`} />
      <span className="font-mono text-xs uppercase tracking-wider text-[var(--color-fg-dim)]">
        {cfg.label}
      </span>
    </div>
  );
}

function PipelinePanel({
  reports,
  active,
  onPick,
  showInternal,
}: {
  reports: Record<string, string>;
  active: string | null;
  onPick: (k: string) => void;
  showInternal: boolean;
}) {
  return (
    <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)]">
      <div className="border-b border-[var(--color-border)] px-4 py-3">
        <div className="font-mono text-xs uppercase tracking-wider text-[var(--color-fg-dim)]">
          Pipeline
        </div>
      </div>
      <ol className="divide-y divide-[var(--color-border)]">
        {ORDER.map((k, idx) => {
          const meta = REPORT_META[k];
          const has = k in reports;
          const isInternal = meta.tone === "internal";
          const hidden = isInternal && !showInternal;
          const isActive = active === k;
          return (
            <li key={k}>
              <button
                onClick={() => has && !hidden && onPick(k)}
                disabled={!has || hidden}
                className={`group flex w-full items-center gap-3 px-4 py-3 text-left transition ${
                  isActive ? "bg-[var(--color-accent-soft)]" : "hover:bg-[var(--color-surface-2)]"
                } ${!has ? "opacity-40" : ""}`}
              >
                <span className="font-mono text-[10px] text-[var(--color-fg-muted)] w-6">
                  {String(idx + 1).padStart(2, "0")}
                </span>
                <span
                  className={`h-1.5 w-1.5 rounded-full ${
                    has
                      ? meta.tone === "analyst"
                        ? "bg-[var(--color-fg)]"
                        : meta.tone === "research"
                        ? "bg-[var(--color-accent)]"
                        : "bg-[var(--color-negative)]"
                      : "bg-[var(--color-fg-muted)] pulse-dot"
                  }`}
                />
                <span className="flex-1 font-mono text-sm">{meta.short}</span>
                {hidden && (
                  <span className="font-mono text-[10px] uppercase tracking-wider text-[var(--color-fg-muted)]">
                    hidden
                  </span>
                )}
              </button>
            </li>
          );
        })}
      </ol>
    </div>
  );
}

function StatusFeed({
  events,
  status,
  endRef,
}: {
  events: StatusEvent[];
  status: Status;
  endRef: React.RefObject<HTMLDivElement | null>;
}) {
  return (
    <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)]">
      <div className="flex items-center justify-between border-b border-[var(--color-border)] px-4 py-3">
        <div className="font-mono text-xs uppercase tracking-wider text-[var(--color-fg-dim)]">
          Activity
        </div>
        {status === "running" && (
          <span className="h-1.5 w-1.5 rounded-full bg-[var(--color-accent)] pulse-dot" />
        )}
      </div>
      <div className="max-h-80 overflow-y-auto p-3 font-mono text-[11px] leading-relaxed">
        {events.length === 0 ? (
          <div className="text-[var(--color-fg-muted)] italic p-2">
            Waiting for agents…
          </div>
        ) : (
          events.map((e, i) => (
            <div key={i} className="flex gap-2 py-1">
              <span className="text-[var(--color-fg-muted)] shrink-0">
                {new Date(e.ts).toLocaleTimeString([], { hour12: false })}
              </span>
              <span className="text-[var(--color-fg-dim)] break-words">
                {e.message ?? e.error ?? ""}
              </span>
            </div>
          ))
        )}
        <div ref={endRef} />
      </div>
    </div>
  );
}

function DossierPanel({
  run,
  reports,
  active,
  visibleReports,
  showInternal,
  setShowInternal,
  status,
}: {
  run: RunDetail | null;
  reports: Record<string, string>;
  active: string | null;
  visibleReports: string[];
  showInternal: boolean;
  setShowInternal: (v: boolean) => void;
  status: Status;
}) {
  const activeKey = active && active in reports ? active : visibleReports[0];
  const meta = activeKey ? REPORT_META[activeKey] : null;
  const content = activeKey ? reports[activeKey] : null;
  const hasAny = visibleReports.length > 0;
  const ticker = run?.ticker ?? "dossier";
  const date = run?.trade_date ?? "";

  function exportPdf() {
    // Set a print-friendly document title so the browser's Save-as-PDF
    // dialog suggests "PALLISADE-<TICKER>-<DATE>.pdf" by default.
    const prev = document.title;
    document.title = `PALLISADE-${ticker}-${date}`.replace(/[^A-Za-z0-9._-]+/g, "_");
    const restore = () => {
      document.title = prev;
      window.removeEventListener("afterprint", restore);
    };
    window.addEventListener("afterprint", restore);
    // requestAnimationFrame to let the title swap commit before print().
    requestAnimationFrame(() => window.print());
  }

  return (
    <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] min-h-[60vh]">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--color-border)] px-5 py-3.5">
        <div>
          <div className="font-mono text-[10px] uppercase tracking-widest text-[var(--color-fg-muted)]">
            {meta?.tone ?? "—"}
          </div>
          <div className="mt-0.5 font-mono text-sm">{meta?.label ?? "No report yet"}</div>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={exportPdf}
            disabled={!hasAny}
            title={hasAny ? "Print all visible reports as PDF" : "No reports to export yet"}
            className="flex items-center gap-2 rounded-md border border-[var(--color-border)] bg-[var(--color-surface-2)] px-3 py-1.5 font-mono text-[10px] uppercase tracking-wider text-[var(--color-fg-dim)] transition hover:border-[var(--color-accent)] hover:text-[var(--color-fg)] disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:border-[var(--color-border)] disabled:hover:text-[var(--color-fg-dim)]"
          >
            <span aria-hidden>↓</span>
            Export PDF
          </button>
          <InternalToggle showInternal={showInternal} setShowInternal={setShowInternal} />
        </div>
      </div>

      <div className="px-5 py-5">
        {!content && status === "running" && (
          <div className="flex items-center gap-3 text-sm text-[var(--color-fg-dim)] font-mono">
            <span className="h-1.5 w-1.5 rounded-full bg-[var(--color-accent)] pulse-dot" />
            Agents are working — reports will appear here as they are produced.
          </div>
        )}
        {!content && status !== "running" && (
          <div className="text-sm text-[var(--color-fg-muted)] font-mono italic">
            No report selected.
          </div>
        )}
        {content && meta?.tone === "internal" && (
          <div className="mb-4 rounded-md border border-[var(--color-negative)]/40 bg-[var(--color-negative)]/5 p-3 font-mono text-[11px] text-[var(--color-negative)]">
            Internal model output. Surfaced for research review only. <strong>Not a recommendation.</strong>
            Users must form their own conclusion.
          </div>
        )}
        {content && (
          <article className="prose-research max-w-none">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
          </article>
        )}
      </div>
    </div>
  );
}

function InternalToggle({
  showInternal,
  setShowInternal,
}: {
  showInternal: boolean;
  setShowInternal: (v: boolean) => void;
}) {
  return (
    <button
      onClick={() => setShowInternal(!showInternal)}
      className="flex items-center gap-2 rounded-md border border-[var(--color-border)] bg-[var(--color-surface-2)] px-3 py-1.5 font-mono text-[10px] uppercase tracking-wider text-[var(--color-fg-dim)] hover:border-[var(--color-fg-muted)] transition"
      title="Internal verdict is hidden by default. Reveal only for research review."
    >
      <span
        className={`h-1.5 w-1.5 rounded-full ${
          showInternal ? "bg-[var(--color-negative)]" : "bg-[var(--color-fg-muted)]"
        }`}
      />
      {showInternal ? "Hide internal verdict" : "Reveal internal verdict"}
    </button>
  );
}
