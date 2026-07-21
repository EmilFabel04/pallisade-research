"use client";

export type DeltaTone = "ok" | "err" | "neutral";

const deltaColor: Record<DeltaTone, string> = {
  ok: "text-[var(--tone-ok-fg)]",
  err: "text-[var(--color-accent)]",
  neutral: "text-[var(--color-fg-muted)]",
};

export function KPI({
  label,
  value,
  delta,
  deltaTone = "neutral",
  className = "",
}: {
  label: string;
  value: string | number;
  delta?: string;
  deltaTone?: DeltaTone;
  className?: string;
}) {
  return (
    <div
      className={
        "flex flex-col gap-1 rounded-lg border border-[var(--color-border)] " +
        "bg-[var(--color-surface-2)] p-3 " +
        className
      }
    >
      <span className="font-mono text-[10px] uppercase tracking-widest text-[var(--color-fg-muted)]">
        {label}
      </span>
      <span className="text-lg font-semibold text-[var(--color-fg)]">
        {value}
      </span>
      {delta !== undefined && (
        <span className={`font-mono text-[11px] ${deltaColor[deltaTone]}`}>
          {delta}
        </span>
      )}
    </div>
  );
}
