/** Compact relative age, e.g. "5m ago" / "3h ago" / "2d ago". */
export function timeAgo(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime();
  if (ms < 0) return "just now";
  const h = Math.floor(ms / 3_600_000);
  if (h < 1) return `${Math.max(1, Math.floor(ms / 60_000))}m ago`;
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

/** Absolute local datetime for a hover title. */
export function absoluteTime(iso: string): string {
  return new Date(iso).toLocaleString();
}
