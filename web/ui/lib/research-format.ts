// web/ui/lib/research-format.ts
import type { ResearchRecord } from "./research";

export const SERIF = { fontFamily: '"Source Serif 4", serif' } as const;

const KEY_LABELS: Record<string, string> = {
  "fundamentals.marketCap": "Market capitalisation",
  "fundamentals.trailingPE": "Trailing P/E",
  "fundamentals.totalRevenue": "Revenue (ttm)",
  "fundamentals.profitMargins": "Profit margin",
};

export function abbrevUsd(n: number): string {
  const a = Math.abs(n);
  if (a >= 1e12) return `$${(n / 1e12).toFixed(2)}T`;
  if (a >= 1e9) return `$${(n / 1e9).toFixed(1)}B`;
  if (a >= 1e6) return `$${(n / 1e6).toFixed(1)}M`;
  if (a >= 1e3) return `$${(n / 1e3).toFixed(0)}K`;
  return `$${n.toFixed(0)}`;
}

function prettifyKey(key: string): string {
  const tail = key.includes(".") ? key.slice(key.indexOf(".") + 1) : key;
  const spaced = tail.replace(/([a-z])([A-Z])/g, "$1 $2").replace(/[._]/g, " ");
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}

export function formatRecord(rec: ResearchRecord): { label: string; display: string } {
  const { key, value } = rec;
  const label = KEY_LABELS[key] ?? prettifyKey(key);

  if (key.startsWith("holdings.") && value && typeof value === "object") {
    const v = value as { units?: number; value?: number };
    const units = v.units?.toLocaleString() ?? "—";
    const worth = v.value != null ? `$${v.value.toLocaleString()}` : "—";
    return { label: "Your position", display: `${units} units · ${worth}` };
  }
  if (typeof value === "number") {
    if (key.endsWith("marketCap") || key.endsWith("totalRevenue"))
      return { label, display: abbrevUsd(value) };
    if (key.endsWith("trailingPE")) return { label, display: `${value.toFixed(1)}×` };
    if (key.toLowerCase().includes("margin"))
      return { label, display: `${(value * 100).toFixed(1)}%` };
    return { label, display: value.toLocaleString() };
  }
  return { label, display: String(value) };
}

/**
 * Safety net for a narration that is supposed to be plain prose. Strips stray
 * block-level Markdown markers (headings, blockquotes, list bullets) that the
 * model occasionally emits despite being told not to — so they never render as
 * literal `##` / `>` characters. Inline **bold** is left intact for the inline
 * renderer below.
 */
export function stripBlockMarkdown(line: string): string {
  return line
    .replace(/^\s*#{1,6}\s+/, "") // # headings
    .replace(/^\s*>\s?/, "") // > blockquotes
    .replace(/^\s*[-*+]\s+/, "") // - / * / + bullets
    .replace(/^\s*\d+\.\s+/, ""); // 1. numbered lists
}

/** Minimal inline renderer: **bold** + [source] chips, newline-aware. Returns React-ready segments. */
export function inlineSegments(text: string): Array<{ t: "text" | "bold" | "cite"; v: string }> {
  const out: Array<{ t: "text" | "bold" | "cite"; v: string }> = [];
  // split on **bold** and [cite]
  const re = /(\*\*[^*]+\*\*|\[[^\]]+\])/g;
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) out.push({ t: "text", v: text.slice(last, m.index) });
    const tok = m[0];
    if (tok.startsWith("**")) out.push({ t: "bold", v: tok.slice(2, -2) });
    else out.push({ t: "cite", v: tok.slice(1, -1) });
    last = m.index + tok.length;
  }
  if (last < text.length) out.push({ t: "text", v: text.slice(last) });
  return out;
}
