"use client";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const KIND_LABEL: Record<string, string> = {
  market_report: "Market report",
  sentiment_report: "Sentiment report",
  news_report: "News report",
  fundamentals_report: "Fundamentals report",
  investment_plan: "Investment plan",
  trader_investment_plan: "Red Team pre-mortem",
  final_trade_decision: "Final decision",
};

export function MemoView({
  title, body_md, ticker, kind, source_run,
}: {
  title: string; body_md: string; ticker: string; kind: string;
  source_run?: { id: string; ticker: string; created_at: string } | null;
}) {
  return (
    <article className="prose-research max-w-none">
      <header className="not-prose mb-6 border-b border-[var(--color-border)] pb-4">
        <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-widest text-[var(--color-fg-muted)]">
          <span>{ticker}</span>
          <span>·</span>
          <span>{KIND_LABEL[kind] ?? kind}</span>
        </div>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight">{title}</h1>
        {source_run ? (
          <p className="mt-1 text-xs text-[var(--color-fg-muted)]">
            From run <code className="font-mono">{source_run.id.slice(0, 8)}</code>{" "}
            on {new Date(source_run.created_at).toLocaleDateString()}
          </p>
        ) : null}
      </header>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{body_md}</ReactMarkdown>
    </article>
  );
}
